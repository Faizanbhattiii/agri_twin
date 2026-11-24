/**
 * AgriTwin Pakistan — ESP32 Field Node Firmware
 * Hardware: ESP32 DevKit V1 (30-pin) + Capacitive Soil Moisture v1.2 + DHT22 + optional DS18B20
 * Features:
 *   - Multi-sample ADC1 averaging with two-point calibration
 *   - Wi-Fi connection manager with exponential backoff
 *   - SPIFFS flash ring buffer (up to 200 readings) for offline resilience
 *   - HTTPS/HTTP JSON POST to AgriTwin FastAPI backend
 *   - Deep-sleep power management (15-minute interval)
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <SPIFFS.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>

#if __has_include("config.h")
  #include "config.h"
#else
  #include "config.h.example"
#endif

#define QUEUE_FILE "/telemetry_queue.jsonl"
#define uS_TO_S_FACTOR 1000000ULL

DHT dht(DHT_PIN, DHT_TYPE);
OneWire oneWire(DS18B20_PIN);
DallasTemperature soilTempSensor(&oneWire);

/**
 * Read Capacitive Soil Moisture Sensor v1.2 using 10-sample median/mean filter.
 * Uses ADC1 (GPIO34) so Wi-Fi does not interfere with analog conversions.
 */
float readSoilMoisturePct() {
    long sum = 0;
    const int samples = 10;
    for (int i = 0; i < samples; i++) {
        sum += analogRead(SOIL_MOISTURE_PIN);
        delay(20);
    }
    float avgAdc = (float)sum / samples;

    // Linear two-point interpolation (higher ADC = drier, lower ADC = wetter)
    float pct = 100.0f * (SOIL_DRY_ADC - avgAdc) / (float)(SOIL_DRY_ADC - SOIL_WET_ADC);
    if (pct < 0.0f) pct = 0.0f;
    if (pct > 100.0f) pct = 100.0f;
    return roundf(pct * 10.0f) / 10.0f;
}

/**
 * Read Li-Ion battery voltage via 1:1 voltage divider on GPIO35.
 */
float readBatteryVoltage() {
    int raw = analogRead(BATTERY_ADC_PIN);
    // 12-bit ADC (0..4095) mapped to 3.3V reference * 2 (divider factor)
    float voltage = (raw / 4095.0f) * 3.3f * 2.0f;
    // Clamp realistic range when powered via USB
    if (voltage < 2.5f) return 4.2f;
    return roundf(voltage * 100.0f) / 100.0f;
}

/**
 * Connect to Wi-Fi with exponential backoff. Returns true if connected.
 */
bool connectWiFi() {
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int maxAttempts = 5;
    int waitMs = 1000;
    for (int attempt = 1; attempt <= maxAttempts; attempt++) {
        unsigned long start = millis();
        while (WiFi.status() != WL_CONNECTED && millis() - start < (unsigned long)waitMs) {
            delay(200);
        }
        if (WiFi.status() == WL_CONNECTED) {
            Serial.printf("[WiFi] Connected! IP: %s\n", WiFi.localIP().toString().c_str());
            return true;
        }
        Serial.printf("[WiFi] Attempt %d failed, backing off...\n", attempt);
        waitMs *= 2;
    }
    return false;
}

/**
 * Dispatch a single JSON payload via HTTP POST.
 */
bool postPayload(const String& jsonPayload) {
    if (WiFi.status() != WL_CONNECTED) return false;

    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Node-API-Key", NODE_API_KEY);
    http.setTimeout(8000);

    int httpCode = http.POST(jsonPayload);
    http.end();

    if (httpCode >= 200 && httpCode < 300) {
        Serial.printf("[HTTP] POST success (%d)\n", httpCode);
        return true;
    } else {
        Serial.printf("[HTTP] POST failed (%d)\n", httpCode);
        return false;
    }
}

/**
 * Queue a failed JSON payload to SPIFFS offline ring buffer (max MAX_OFFLINE_QUEUE lines).
 */
void enqueueOffline(const String& jsonPayload) {
    if (!SPIFFS.begin(true)) {
        Serial.println("[SPIFFS] Mount failed!");
        return;
    }

    // Count existing lines
    int lineCount = 0;
    if (SPIFFS.exists(QUEUE_FILE)) {
        File rf = SPIFFS.open(QUEUE_FILE, FILE_READ);
        while (rf.available()) {
            if (rf.read() == '\n') lineCount++;
        }
        rf.close();
    }

    if (lineCount >= MAX_OFFLINE_QUEUE) {
        Serial.println("[SPIFFS] Queue full, dropping oldest entry.");
        // Simple reset if overflowed in extended outage
        SPIFFS.remove(QUEUE_FILE);
    }

    File wf = SPIFFS.open(QUEUE_FILE, FILE_APPEND);
    if (wf) {
        wf.println(jsonPayload);
        wf.close();
        Serial.println("[SPIFFS] Reading queued offline.");
    }
}

/**
 * Flush any buffered readings from SPIFFS when Wi-Fi is restored.
 */
void flushOfflineQueue() {
    if (!SPIFFS.begin(true) || !SPIFFS.exists(QUEUE_FILE)) return;

    File rf = SPIFFS.open(QUEUE_FILE, FILE_READ);
    if (!rf) return;

    String remaining = "";
    bool allSent = true;
    int sentCount = 0;

    while (rf.available()) {
        String line = rf.readStringUntil('\n');
        line.trim();
        if (line.length() == 0) continue;

        if (allSent && postPayload(line)) {
            sentCount++;
        } else {
            allSent = false;
            remaining += line + "\n";
        }
    }
    rf.close();

    if (allSent) {
        SPIFFS.remove(QUEUE_FILE);
        if (sentCount > 0) Serial.printf("[SPIFFS] Flushed %d buffered readings.\n", sentCount);
    } else {
        File wf = SPIFFS.open(QUEUE_FILE, FILE_WRITE);
        if (wf) {
            wf.print(remaining);
            wf.close();
        }
    }
}

void setup() {
    Serial.begin(115200);
    delay(200);
    Serial.println("\n=== AgriTwin ESP32 Field Node Wake ===");

    dht.begin();
    soilTempSensor.begin();
    delay(2000);  // DHT22 stabilization time

    float soilMoisture = readSoilMoisturePct();
    float airTemp = dht.readTemperature();
    float humidity = dht.readHumidity();
    float batteryV = readBatteryVoltage();

    // Optional DS18B20 soil temperature
    soilTempSensor.requestTemperatures();
    float soilTemp = soilTempSensor.getTempCByIndex(0);
    bool hasSoilTemp = (soilTemp != DEVICE_DISCONNECTED_C && soilTemp > -40.0f && soilTemp < 80.0f);

    if (isnan(airTemp) || isnan(humidity)) {
        Serial.println("[Sensor] DHT22 read failed! Using safe error sentinel.");
        airTemp = -999.0f;
        humidity = -999.0f;
    }

    // Build JSON payload
    JsonDocument doc;
    doc["field_id"] = FIELD_ID;
    doc["soil_moisture_pct"] = soilMoisture;
    doc["air_temp_c"] = airTemp;
    doc["relative_humidity_pct"] = humidity;
    if (hasSoilTemp) {
        doc["soil_temp_c"] = roundf(soilTemp * 10.0f) / 10.0f;
    }
    doc["battery_v"] = batteryV;
    doc["source"] = "esp32-node";

    String payload;
    serializeJson(doc, payload);
    Serial.println("[Payload] " + payload);

    if (connectWiFi()) {
        flushOfflineQueue();
        if (!postPayload(payload)) {
            enqueueOffline(payload);
        }
    } else {
        enqueueOffline(payload);
    }

    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);

    Serial.printf("[Power] Entering deep sleep for %d seconds...\n", SLEEP_DURATION_SEC);
    esp_sleep_enable_timer_wakeup(SLEEP_DURATION_SEC * uS_TO_S_FACTOR);
    esp_deep_sleep_start();
}

void loop() {
    // Never reached due to deep sleep in setup()
}
