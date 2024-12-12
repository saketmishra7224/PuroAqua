#include <Wire.h>
#include <Adafruit_TCS34725.h>
#include <WiFi.h>
#include <LiquidCrystal_I2C.h>
#include <PubSubClient.h>
#include <math.h>

const char* aws_endpoint = "your-aws-endpoint.amazonaws.com";
const char* mqtt_topic = "esp32/colorData";
const char* ssid = "your_SSID";
const char* password = "your_PASSWORD";

Adafruit_TCS34725 tcs = Adafruit_TCS34725(TCS34725_INTEGRATIONTIME_700MS, TCS34725_GAIN_1X);
LiquidCrystal_I2C lcd(0x27, 16, 2);

WiFiClient espClient;
PubSubClient client(espClient);

#define THRESHOLD 15.0  

struct ColorLevel {
    const char* name;
    uint8_t r, g, b;
    uint8_t level;
};

ColorLevel color_levels[] = {
    {"Sea Nymph", 130, 159, 152, 1},
    {"Metallic Seaweed", 38, 127, 140, 2},
    {"Metallic Seaweed", 26, 127, 147, 3},
    {"Regal Blue", 0, 71, 119, 4},
    {"Cod Grey", 13, 12, 12, 5},
};

float calculateColorDistance(uint16_t r1, uint16_t g1, uint16_t b1, uint8_t r2, uint8_t g2, uint8_t b2) {
    return sqrt(pow(r1 - r2, 2) + pow(g1 - g2, 2) + pow(b1 - b2, 2));
}

const char* getColorLevel(uint16_t r, uint16_t g, uint16_t b, uint8_t* level) {
    float minDistance = THRESHOLD + 1;
    const char* closestColor = "Unknown";
    *level = 0;

    for (auto& color : color_levels) {
        float distance = calculateColorDistance(r, g, b, color.r, color.g, color.b);
        if (distance < minDistance) {
            minDistance = distance;
            closestColor = color.name;
            *level = color.level;
        }
    }

    return (minDistance > THRESHOLD) ? "Unknown" : closestColor;
}

void connectToWiFi() {
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
  }
}

void connectToAWS() {
  client.setServer(aws_endpoint, 8883);
  while (!client.connected()) {
    if (client.connect("ESP32_Client")) {
      // Connected to AWS IoT
    } else {
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  lcd.begin();
  lcd.backlight();

  if (tcs.begin()) {
    lcd.setCursor(0, 0);
    lcd.print("Sensor Ready");
  } else {
    while (1);
  }

  connectToWiFi();
  connectToAWS();
}

void loop() {
  uint16_t r, g, b, c;
  tcs.getRawData(&r, &g, &b, &c);

  float red = r;
  float green = g;
  float blue = b;

  uint8_t alert_level;
  const char* color_name = getColorLevel(r, g, b, &alert_level);

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(color_name);
  lcd.setCursor(0, 1);
  if (alert_level != 0) {
    lcd.print("Level:");
    lcd.print(alert_level);
  } else {
    lcd.print("Unknown");
  }

  Serial.print("R: "); Serial.print(red); 
  Serial.print(" G: "); Serial.print(green); 
  Serial.print(" B: "); Serial.println(blue);
  Serial.print("Color: "); Serial.println(color_name);
  Serial.print("Alert Level: "); Serial.println(alert_level);

  String jsonPayload = "{\"color\":\"" + String(color_name) + "\",\"alert_level\":" + String(alert_level) + "}";

  if (client.connected()) {
    client.publish(mqtt_topic, jsonPayload.c_str());
  }

  delay(5000);
}
