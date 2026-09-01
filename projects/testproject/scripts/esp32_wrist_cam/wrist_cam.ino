// Wrist camera server for the XIAO ESP32-S3 Sense.
//
// Serves exactly the interface the SO-101 client already speaks, so no change
// is needed on the robot side - only --wrist_url is repointed:
//
//     GET /frame   -> one JPEG, 640x480
//                     header X-Frame-Age-Seconds (the client logs this and we
//                     use it to detect a frozen camera; on this board it is
//                     always ~0 because the frame is captured on demand)
//     GET /health  -> plain text, for pre-run checks
//     GET /stream  -> MJPEG, plays as live video in any browser
//     GET /        -> a page showing the stream, for eyeballing the mount
//
// This replaces the SD-card sketch that shipped on the board, which looped on
// a missing card and never joined WiFi.
//
// FILL IN YOUR WIFI DETAILS BELOW, then it can be flashed.

#include "WiFi.h"
#include "esp_camera.h"
#include "esp_http_server.h"

// ---------------------------------------------------------------- EDIT THESE
const char *WIFI_SSID = "PUT_YOUR_WIFI_NAME_HERE";
const char *WIFI_PASS = "PUT_YOUR_WIFI_PASSWORD_HERE";
// ---------------------------------------------------------------------------

// XIAO ESP32-S3 Sense camera pin map (from the Seeed board definition)
#define PWDN_GPIO_NUM -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 10
#define SIOD_GPIO_NUM 40
#define SIOC_GPIO_NUM 39
#define Y9_GPIO_NUM 48
#define Y8_GPIO_NUM 11
#define Y7_GPIO_NUM 12
#define Y6_GPIO_NUM 14
#define Y5_GPIO_NUM 16
#define Y4_GPIO_NUM 18
#define Y3_GPIO_NUM 17
#define Y2_GPIO_NUM 15
#define VSYNC_GPIO_NUM 38
#define HREF_GPIO_NUM 47
#define PCLK_GPIO_NUM 13

static httpd_handle_t server = NULL;

static esp_err_t frame_handler(httpd_req_t *req) {
  uint32_t t0 = millis();
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }
  // age in seconds, matching the Pi proxy's header so the robot client's
  // staleness check works unchanged
  char age[16];
  snprintf(age, sizeof(age), "%.3f", (millis() - t0) / 1000.0);
  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "X-Frame-Age-Seconds", age);
  esp_err_t r = httpd_resp_send(req, (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
  return r;
}

// MJPEG stream: multipart/x-mixed-replace is what browsers play as live video.
// Serving frames as fast as the sensor produces them also DRAINS the frame
// buffers, which is what the FB-OVF warnings were complaining about while
// nothing was reading them.
#define BOUNDARY "frameboundary"
static const char *STREAM_TYPE = "multipart/x-mixed-replace;boundary=" BOUNDARY;
static const char *STREAM_BOUNDARY = "\r\n--" BOUNDARY "\r\n";
static const char *STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

static esp_err_t stream_handler(httpd_req_t *req) {
  esp_err_t res = httpd_resp_set_type(req, STREAM_TYPE);
  if (res != ESP_OK) return res;
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  char part[64];
  while (true) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) { res = ESP_FAIL; break; }
    size_t hlen = snprintf(part, sizeof(part), STREAM_PART, fb->len);
    res = httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY));
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, part, hlen);
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
    esp_camera_fb_return(fb);
    if (res != ESP_OK) break;      // browser closed the tab
  }
  return res;
}

static esp_err_t index_handler(httpd_req_t *req) {
  static const char page[] =
    "<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'>"
    "<title>SO-101 wrist camera</title>"
    "<style>body{margin:0;background:#141414;color:#eee;font:15px system-ui;"
    "display:flex;flex-direction:column;align-items:center;gap:12px;padding:16px}"
    "img{max-width:100%;border-radius:8px}a{color:#7ab7ff}</style>"
    "<h3>SO-101 wrist camera</h3>"
    "<img src='/stream'>"
    "<div><a href='/frame'>single frame</a> &middot; <a href='/health'>health</a></div>";
  httpd_resp_set_type(req, "text/html");
  return httpd_resp_send(req, page, strlen(page));
}

static esp_err_t health_handler(httpd_req_t *req) {
  char buf[128];
  snprintf(buf, sizeof(buf), "ok rssi=%d ip=%s uptime_s=%lu\n",
           WiFi.RSSI(), WiFi.localIP().toString().c_str(), millis() / 1000);
  httpd_resp_set_type(req, "text/plain");
  return httpd_resp_send(req, buf, strlen(buf));
}

void startServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 8092;          // same port the Pi proxy used
  config.ctrl_port = 8093;
  config.max_open_sockets = 4;   // stream + robot /frame fetches at once
  httpd_uri_t frame_uri = {"/frame", HTTP_GET, frame_handler, NULL};
  httpd_uri_t health_uri = {"/health", HTTP_GET, health_handler, NULL};
  httpd_uri_t stream_uri = {"/stream", HTTP_GET, stream_handler, NULL};
  httpd_uri_t index_uri = {"/", HTTP_GET, index_handler, NULL};
  if (httpd_start(&server, &config) == ESP_OK) {
    httpd_register_uri_handler(server, &frame_uri);
    httpd_register_uri_handler(server, &health_uri);
    httpd_register_uri_handler(server, &stream_uri);
    httpd_register_uri_handler(server, &index_uri);
    Serial.println("HTTP server on :8092  (/, /stream, /frame, /health)");
  }
}

void setup() {
  Serial.begin(115200);
  delay(300);

  camera_config_t c;
  c.ledc_channel = LEDC_CHANNEL_0;
  c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = Y2_GPIO_NUM;  c.pin_d1 = Y3_GPIO_NUM;
  c.pin_d2 = Y4_GPIO_NUM;  c.pin_d3 = Y5_GPIO_NUM;
  c.pin_d4 = Y6_GPIO_NUM;  c.pin_d5 = Y7_GPIO_NUM;
  c.pin_d6 = Y8_GPIO_NUM;  c.pin_d7 = Y9_GPIO_NUM;
  c.pin_xclk = XCLK_GPIO_NUM;   c.pin_pclk = PCLK_GPIO_NUM;
  c.pin_vsync = VSYNC_GPIO_NUM; c.pin_href = HREF_GPIO_NUM;
  c.pin_sccb_sda = SIOD_GPIO_NUM; c.pin_sccb_scl = SIOC_GPIO_NUM;
  c.pin_pwdn = PWDN_GPIO_NUM;   c.pin_reset = RESET_GPIO_NUM;
  c.xclk_freq_hz = 20000000;
  c.frame_size = FRAMESIZE_VGA;   // 640x480 - what the policy was trained on
  c.pixel_format = PIXFORMAT_JPEG;
  c.grab_mode = CAMERA_GRAB_LATEST;   // freshest frame, never a queued stale one
  c.fb_location = CAMERA_FB_IN_PSRAM;
  c.jpeg_quality = 10;            // lower number = better quality
  c.fb_count = 2;

  if (esp_camera_init(&c) != ESP_OK) {
    Serial.println("CAMERA INIT FAILED");
    return;
  }
  // The sensor sits upside down relative to the board, so the picture arrives
  // rotated 180 degrees. vflip + hmirror together are that rotation, applied
  // in the sensor itself.
  sensor_t *sensor = esp_camera_sensor_get();
  if (sensor) {
    sensor->set_vflip(sensor, 1);
    sensor->set_hmirror(sensor, 1);
  }
  Serial.println("camera ok 640x480 jpeg, rotated 180");

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("joining wifi");
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WIFI OK  ip=");
    Serial.println(WiFi.localIP());
    startServer();
  } else {
    Serial.println("WIFI FAILED - check the SSID and password in the sketch");
  }
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("wifi dropped, reconnecting");
    WiFi.reconnect();
    delay(3000);
  }
  delay(1000);
}
