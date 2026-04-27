#include <WiFi.h>
#include <WebSocketsClient.h>
#include <driver/i2s.h>
#include <Wire.h>
#include <hd44780.h>
#include <hd44780ioClass/hd44780_I2Cexp.h>

const char* ssid = "Harsh's Galaxy A21s";
const char* password = "datachor";
const char* backend_ip = "192.168.0.100"; // CHANGE TO BACKEND IP

WebSocketsClient webSocket;
hd44780_I2Cexp lcd;

// ---------------- PINS ----------------
#define TOUCH_PIN 18
#define LED_PIN 4
#define SPK_LED_PIN 5

// MIC
#define MIC_WS 25
#define MIC_SCK 26
#define MIC_SD 22

// SPEAKER
#define SPK_WS 33
#define SPK_BCK 32
#define SPK_DOUT 19

#define SAMPLE_RATE 16000
#define MIC_BUFFER 512
#define SPK_DMA_LEN 64
#define PLAY_TIMEOUT 5000
#define DEBOUNCE_DELAY 300
#define AUDIO_GAIN 3.5

typedef enum {
  IDLE,
  RECORDING,
  PROCESSING,
  PLAYING
} State;

State currentState = IDLE;

int16_t spkBuf[128];
int bufIdx = 0;

int expectedBytes = 0;
int receivedBytes = 0;
bool expectingSize = false;

unsigned long playStart = 0;
unsigned long processingStart = 0;
unsigned long lastDebounce = 0;

// ---------------- HELPERS ----------------

void setLEDs(bool red, bool green) {
  digitalWrite(LED_PIN, red);
  digitalWrite(SPK_LED_PIN, green);
}

void goIdle() {
  currentState = IDLE;
  setLEDs(false, false);
  bufIdx = 0;
  expectedBytes = 0;
  receivedBytes = 0;
  expectingSize = false;

  i2s_zero_dma_buffer(I2S_NUM_1);
  delay(20);

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("AI Assistant");
  lcd.setCursor(0, 1);
  lcd.print("Touch to talk");
  Serial.println("[READY]");
}

// ---------------- MIC ----------------

void setupMic() {
  i2s_config_t cfg = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = MIC_BUFFER
  };
  i2s_pin_config_t pins = {
    .bck_io_num = MIC_SCK,
    .ws_io_num = MIC_WS,
    .data_out_num = -1,
    .data_in_num = MIC_SD
  };
  i2s_driver_install(I2S_NUM_0, &cfg, 0, NULL);
  i2s_set_pin(I2S_NUM_0, &pins);
}

// ---------------- SPEAKER ----------------

void setupSpeaker() {
  i2s_config_t cfg = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = SPK_DMA_LEN
  };
  i2s_pin_config_t pins = {
    .bck_io_num = SPK_BCK,
    .ws_io_num = SPK_WS,
    .data_out_num = SPK_DOUT,
    .data_in_num = -1
  };
  i2s_driver_install(I2S_NUM_1, &cfg, 0, NULL);
  i2s_set_pin(I2S_NUM_1, &pins);

  int16_t silence[64] = {0};
  size_t w;
  i2s_write(I2S_NUM_1, silence, sizeof(silence), &w, portMAX_DELAY);
}

// ---------------- WEBSOCKET ----------------

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  if (type == WStype_TEXT) {
    String text = String((char*)payload);
    if (text.startsWith("LCD:")) {
      String t = text.substring(4);
      t.trim();
      lcd.clear();
      lcd.print(t.substring(0, 16));
    } else if (text == "AUDIO_START") {
      expectingSize = true;
      receivedBytes = 0;
      bufIdx = 0;
      playStart = millis();
      currentState = PLAYING;
      setLEDs(false, true);
    } else if (expectingSize && currentState == PLAYING) {
      expectedBytes = text.toInt();
      expectingSize = false;
      Serial.printf("[WS] Expected audio bytes: %d\n", expectedBytes);
    }
  } else if (type == WStype_BIN) {
    if (currentState == PLAYING) {
      for (size_t i = 0; i < length; i++) {
        ((uint8_t*)spkBuf)[bufIdx * 2 + (receivedBytes % 2)] = payload[i];
        if (receivedBytes % 2 == 1) {
            bufIdx++;
        }
        receivedBytes++;
        
        if (bufIdx >= 128) {
            for (int j = 0; j < 128; j++) {
                int32_t v = (int32_t)(spkBuf[j] * AUDIO_GAIN);
                if (v > 32767) v = 32767;
                if (v < -32768) v = -32768;
                spkBuf[j] = (int16_t)v;
            }
            size_t w;
            i2s_write(I2S_NUM_1, spkBuf, 128 * 2, &w, portMAX_DELAY);
            bufIdx = 0;
        }
      }
      
      if (receivedBytes >= expectedBytes && expectedBytes > 0) {
        if (bufIdx > 0) {
            for (int j = 0; j < bufIdx; j++) {
                int32_t v = (int32_t)(spkBuf[j] * AUDIO_GAIN);
                if (v > 32767) v = 32767;
                if (v < -32768) v = -32768;
                spkBuf[j] = (int16_t)v;
            }
            size_t w;
            i2s_write(I2S_NUM_1, spkBuf, bufIdx * 2, &w, portMAX_DELAY);
        }
        int16_t silence[64] = {0};
        size_t w;
        i2s_write(I2S_NUM_1, silence, sizeof(silence), &w, portMAX_DELAY);
        delay(40);
        goIdle();
      }
    }
  }
}

// ---------------- SETUP ----------------

void setup() {
  Serial.begin(115200);

  pinMode(TOUCH_PIN, INPUT_PULLDOWN);
  pinMode(LED_PIN, OUTPUT);
  pinMode(SPK_LED_PIN, OUTPUT);

  Wire.begin(21, 15);
  lcd.begin(16, 2);
  lcd.backlight();
  lcd.clear();
  lcd.print("Initializing...");

  setupMic();
  setupSpeaker();

  WiFi.begin(ssid, password);
  Serial.print("Connecting WiFi...");
  while(WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected");

  webSocket.begin(backend_ip, 8000, "/ws/voice");
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(5000);

  delay(1000);
  goIdle();
}

// ---------------- RECORD ----------------

void handleRecording() {
  int32_t raw[MIC_BUFFER];
  size_t br = 0;
  i2s_read(I2S_NUM_0, &raw, sizeof(raw), &br, portMAX_DELAY);
  
  uint8_t pcmBuffer[MIC_BUFFER * 2];
  int pcmLen = 0;
  
  for(int i = 0; i < br / 4; i++) {
    int16_t s = (int16_t)(raw[i] >> 16);
    pcmBuffer[pcmLen++] = s & 0xFF;
    pcmBuffer[pcmLen++] = (s >> 8) & 0xFF;
  }
  
  if (pcmLen > 0) {
    webSocket.sendBIN(pcmBuffer, pcmLen);
  }
}

// ---------------- LOOP ----------------

void loop() {
  webSocket.loop();

  static bool last = LOW;
  bool touch = digitalRead(TOUCH_PIN);

  if (touch == HIGH && last == LOW && millis() - lastDebounce > DEBOUNCE_DELAY) {
    lastDebounce = millis();
    if (currentState == IDLE) {
      currentState = RECORDING;
      setLEDs(true, false);
      lcd.clear();
      lcd.print("Listening...");
      webSocket.sendTXT("START");
    } else if (currentState == RECORDING) {
      currentState = PROCESSING;
      processingStart = millis();
      setLEDs(false, false);
      lcd.clear();
      lcd.print("Processing...");
      webSocket.sendTXT("STOP");
    }
  }
  last = touch;

  switch (currentState) {
    case RECORDING:
      handleRecording();
      break;
    case PROCESSING:
      if (millis() - processingStart > 15000) goIdle();
      break;
    case PLAYING:
      if (millis() - playStart > PLAY_TIMEOUT) goIdle();
      break;
    default:
      break;
  }
  delay(1);
}
