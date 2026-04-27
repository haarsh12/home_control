#include <WiFi.h>
#include <HTTPClient.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include "DHT.h"

/* ---------- WIFI ---------- */
const char* ssid = "Harsh's Galaxy A21s";
const char* password = "datachor";
const char* backend_ip = "192.168.105.207"; // CHANGE TO BACKEND IP

WebSocketsClient webSocket;

/* ---------- PINS ---------- */
#define touch1 18
#define touch2 19
#define relay1 5
#define relay2 21
#define MQ2_ANALOG 34
#define MQ2_DIGITAL 4
#define LDR_PIN 35
#define DHTPIN 23
#define DHTTYPE DHT11

DHT dht(DHTPIN, DHTTYPE);

/* ---------- VARIABLES ---------- */
bool relay1State = false;
bool relay2State = false;

bool lastTouch1 = LOW;
bool lastTouch2 = LOW;

unsigned long lastDebounceTime1 = 0;
unsigned long lastDebounceTime2 = 0;
unsigned long debounceDelay = 300;

unsigned long lastSensorRead = 0;
unsigned long sensorInterval = 3000;

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  if (type == WStype_TEXT) {
    Serial.printf("[RELAY WS] Received text: %s\n", payload);
    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, payload);
    if (!error) {
      const char* device = doc["device"];
      bool state = doc["state"];
      if (device && String(device) == "light") {
        relay1State = state;
        digitalWrite(relay1, state ? HIGH : LOW);
        Serial.printf("Light is now %s\n", state ? "ON" : "OFF");
      } else if (device && String(device) == "fan") {
        relay2State = state;
        digitalWrite(relay2, state ? HIGH : LOW);
        Serial.printf("Fan is now %s\n", state ? "ON" : "OFF");
      }
    }
  }
}

void setup() {
  Serial.begin(115200);

  pinMode(touch1, INPUT);
  pinMode(touch2, INPUT);
  pinMode(relay1, OUTPUT);
  pinMode(relay2, OUTPUT);
  pinMode(MQ2_DIGITAL, INPUT);
  pinMode(LDR_PIN, INPUT);

  digitalWrite(relay1, LOW);
  digitalWrite(relay2, LOW);

  dht.begin();
  delay(2000);

  /* WIFI START */
  WiFi.begin(ssid, password);
  Serial.println("Connecting WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());

  webSocket.begin(backend_ip, 8000, "/ws/relay");
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(5000);
}

void loop() {
  webSocket.loop();

  unsigned long currentTime = millis();

  int t1 = digitalRead(touch1);
  int t2 = digitalRead(touch2);

  /* TOUCH LIGHT */
  if (t1 == HIGH && lastTouch1 == LOW && (currentTime - lastDebounceTime1 > debounceDelay)) {
    relay1State = !relay1State;
    digitalWrite(relay1, relay1State ? HIGH : LOW);
    lastDebounceTime1 = currentTime;
    Serial.println("[TOUCH] Relay1 toggled");
  }
  lastTouch1 = t1;

  /* TOUCH FAN */
  if (t2 == HIGH && lastTouch2 == LOW && (currentTime - lastDebounceTime2 > debounceDelay)) {
    relay2State = !relay2State;
    digitalWrite(relay2, relay2State ? HIGH : LOW);
    lastDebounceTime2 = currentTime;
    Serial.println("[TOUCH] Relay2 toggled");
  }
  lastTouch2 = t2;

  /* PERIODIC SENSOR POST */
  if (currentTime - lastSensorRead > sensorInterval) {
    lastSensorRead = currentTime;

    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      String url = String("http://") + String(backend_ip) + ":8000/sensors/data";
      http.begin(url);
      http.addHeader("Content-Type", "application/json");

      String json = "{";
      json += "\"mqAnalog\":" + String(analogRead(MQ2_ANALOG)) + ",";
      json += "\"mqDigital\":" + String(digitalRead(MQ2_DIGITAL)) + ",";
      json += "\"ldr\":" + String(digitalRead(LDR_PIN)) + ",";
      float temp = dht.readTemperature();
      float hum = dht.readHumidity();
      json += "\"temperature\":" + String(isnan(temp) ? -1 : temp) + ",";
      json += "\"humidity\":" + String(isnan(hum) ? -1 : hum);
      json += "}";

      int httpResponseCode = http.POST(json);
      Serial.print("[HTTP] POST /sensors/data -> Response: ");
      Serial.println(httpResponseCode);
      http.end();
    }
  }
}
