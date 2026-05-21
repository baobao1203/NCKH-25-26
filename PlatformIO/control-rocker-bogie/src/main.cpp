/*
 * ===============================================================
 * ROBOT XE - ESP32 30-PIN (PINOUT MỚI - THỰC TẾ ĐÃ NỐI)
 * ===============================================================
 * IBT-2 TRÁI (Motor A):
 *   RPWM → D32  |  LPWM → D25
 *   R_EN → D33  |  L_EN → D26
 *
 * IBT-2 PHẢI (Motor B):
 *   RPWM → D21  |  LPWM → D18
 *   R_EN → D19  |  L_EN → D5
 *
 * 4 SERVO MG996R:
 *   LB (trái sau)   → D27
 *   LF (trái trước) → D14
 *   RF (phải trước) → D23
 *   RB (phải sau)   → D4
 *
 * LED → D2
 * ===============================================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>

const char* WIFI_SSID     = "TenWifiCuaBan";
const char* WIFI_PASSWORD = "MatKhauWifi";
const char* AP_SSID       = "RobotCar";
const char* AP_PASSWORD   = "12345678";

// IBT-2 trái
#define MA_RPWM_PIN  32
#define MA_LPWM_PIN  25
#define MA_REN_PIN   33
#define MA_LEN_PIN   26

// IBT-2 phải
#define MB_RPWM_PIN  21
#define MB_LPWM_PIN  18
#define MB_REN_PIN   19
#define MB_LEN_PIN    5

// Servo
#define SERVO_LB_PIN  27
#define SERVO_LF_PIN  14
#define SERVO_RF_PIN  23
#define SERVO_RB_PIN   4

#define LED_PIN  2

// LEDC Motor (10kHz, 8-bit)
#define CH_MA_RPWM  0
#define CH_MA_LPWM  1
#define CH_MB_RPWM  2
#define CH_MB_LPWM  3

// LEDC Servo (50Hz, 16-bit)
#define CH_SERVO_LB  4
#define CH_SERVO_LF  5
#define CH_SERVO_RF  6
#define CH_SERVO_RB  7

#define SERVO_FREQ   50
#define SERVO_RES    16
#define MOTOR_FREQ   10000
#define MOTOR_RES    8

static const int CENTER    = 90;
static const int MAX_DELTA = 35;
static const int HARD_MIN  = 10;
static const int HARD_MAX  = 170;

int trimLF = 0, trimRF = 0, trimLB = 0, trimRB = 0;
unsigned long lastCmd = 0;
const unsigned long TIMEOUT = 500;

WebServer server(80);

void writeServo(int ch, int angle);
void setSteering(float steer);
void setSpin(float val);
void setMotor(float throttle);
void stopMotors();
void handleRoot();
void handleControl();
void handleStop();
void handleTrim();

const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>Robot Car</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;touch-action:none;-webkit-tap-highlight-color:transparent;user-select:none}
body{background:#0f0f1a;color:#eee;font-family:'Segoe UI',system-ui,sans-serif;height:100dvh;display:flex;flex-direction:column;overflow:hidden}
header{background:linear-gradient(135deg,#1a1a3e,#0d0d2b);padding:14px;text-align:center;border-bottom:1px solid #2a2a5a}
header h1{font-size:17px;letter-spacing:1px;color:#7ecbff}
#status{font-size:11px;color:#888;margin-top:4px;font-family:monospace}
.main{flex:1;display:flex;align-items:center;justify-content:space-around;padding:12px;gap:8px}
.js-wrap{display:flex;flex-direction:column;align-items:center}
.joystick{width:160px;height:160px;background:radial-gradient(circle,#1a2a4a,#0f1a30);border-radius:50%;position:relative;border:2px solid #2a4a7a}
.stick{width:64px;height:64px;background:radial-gradient(circle at 30% 30%,#ff6b6b,#cc3333);border-radius:50%;position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);box-shadow:0 4px 20px rgba(255,50,50,0.3)}
.js-label{margin-top:8px;font-size:11px;color:#666;text-transform:uppercase;letter-spacing:2px}
.btns{display:flex;flex-direction:column;gap:10px}
.btn{padding:14px 20px;font-size:13px;font-weight:700;border:none;border-radius:10px;color:#fff;cursor:pointer;transition:transform 0.1s}
.btn:active{transform:scale(0.95)}
.btn-spin{background:linear-gradient(135deg,#4a6cf7,#2a4cd7)}
.btn-stop{background:linear-gradient(135deg,#555,#333);border:1px solid #666}
.trim-toggle{position:fixed;top:12px;right:12px;background:#222;border:1px solid #444;color:#aaa;padding:6px 12px;border-radius:6px;font-size:11px;cursor:pointer;z-index:10}
#trimPanel{position:fixed;bottom:0;left:0;right:0;background:#1a1a2e;border-top:1px solid #333;padding:12px;display:none;gap:12px;justify-content:center;flex-wrap:wrap;z-index:10}
#trimPanel.show{display:flex}
.trim-item{display:flex;flex-direction:column;align-items:center;gap:4px}
.trim-item label{font-size:10px;color:#888;text-transform:uppercase}
.trim-item input{width:56px;padding:6px;background:#111;color:#7ecbff;border:1px solid #333;border-radius:4px;text-align:center;font-size:13px;font-family:monospace}
.speed-wrap{position:fixed;bottom:60px;left:50%;transform:translateX(-50%);display:flex;align-items:center;gap:8px;background:#1a1a2e;padding:8px 16px;border-radius:20px;border:1px solid #333}
.speed-wrap label{font-size:10px;color:#888;text-transform:uppercase}
.speed-wrap input[type=range]{width:100px;accent-color:#4a6cf7}
.speed-wrap span{font-size:12px;color:#7ecbff;font-family:monospace;min-width:30px}
</style>
</head>
<body>
<header>
  <h1>ROBOT CAR CONTROL</h1>
  <div id="status">Dang ket noi...</div>
</header>
<button class="trim-toggle" onclick="document.getElementById('trimPanel').classList.toggle('show')">Trim</button>
<div class="main">
  <div class="js-wrap">
    <div class="joystick" id="js"><div class="stick" id="sk"></div></div>
    <div class="js-label">Lai + Ga</div>
  </div>
  <div class="btns">
    <button class="btn btn-spin" ontouchstart="spin(-1)" ontouchend="spin(0)" onmousedown="spin(-1)" onmouseup="spin(0)">Xoay trai</button>
    <button class="btn btn-spin" ontouchstart="spin(1)"  ontouchend="spin(0)" onmousedown="spin(1)"  onmouseup="spin(0)">Xoay phai</button>
    <button class="btn btn-stop" onclick="eStop()">DUNG KHAN CAP</button>
  </div>
</div>
<div class="speed-wrap">
  <label>Toc do</label>
  <input type="range" id="maxSpd" min="20" max="100" value="60" oninput="document.getElementById('spdVal').textContent=this.value+'%'">
  <span id="spdVal">60%</span>
</div>
<div id="trimPanel">
  <div class="trim-item"><label>LF</label><input id="tLF" type="number" value="0" onchange="sendTrim()"></div>
  <div class="trim-item"><label>RF</label><input id="tRF" type="number" value="0" onchange="sendTrim()"></div>
  <div class="trim-item"><label>LB</label><input id="tLB" type="number" value="0" onchange="sendTrim()"></div>
  <div class="trim-item"><label>RB</label><input id="tRB" type="number" value="0" onchange="sendTrim()"></div>
</div>
<script>
const S={steer:0,throttle:0,spin:0};
let busy=false;
(()=>{
  const js=document.getElementById('js'),sk=document.getElementById('sk');
  let on=false;const R=55;
  const go=e=>{on=true;e.preventDefault()};
  const no=()=>{on=false;sk.style.transform='translate(-50%,-50%)';S.steer=0;S.throttle=0};
  const mv=e=>{
    if(!on)return;e.preventDefault();
    const t=e.touches?e.touches[0]:e,r=js.getBoundingClientRect();
    let dx=t.clientX-r.left-r.width/2,dy=t.clientY-r.top-r.height/2;
    const d=Math.min(Math.hypot(dx,dy),R),a=Math.atan2(dy,dx);
    dx=Math.cos(a)*d;dy=Math.sin(a)*d;
    sk.style.transform=`translate(calc(-50% + ${dx}px),calc(-50% + ${dy}px))`;
    S.steer=dx/R;S.throttle=-dy/R;
  };
  js.addEventListener('touchstart',go);js.addEventListener('touchmove',mv);js.addEventListener('touchend',no);
  js.addEventListener('mousedown',go);document.addEventListener('mousemove',mv);document.addEventListener('mouseup',no);
})();
function spin(v){S.spin=v}
function eStop(){S.steer=0;S.throttle=0;S.spin=0;fetch('/stop').then(()=>{document.getElementById('status').textContent='Da dung'})}
function sendTrim(){
  fetch('/trim',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({lf:+document.getElementById('tLF').value||0,rf:+document.getElementById('tRF').value||0,lb:+document.getElementById('tLB').value||0,rb:+document.getElementById('tRB').value||0})});
}
setInterval(async()=>{
  if(busy)return;busy=true;
  const maxS=(+document.getElementById('maxSpd').value)/100;
  const d={steer:S.steer,throttle:S.throttle*maxS,spin:S.spin*maxS};
  try{
    await fetch('/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});
    document.getElementById('status').textContent='Lai:'+S.steer.toFixed(2)+' Ga:'+d.throttle.toFixed(2)+' Xoay:'+d.spin.toFixed(2);
  }catch(e){document.getElementById('status').textContent='Mat ket noi!'}
  busy=false;
},50);
</script>
</body>
</html>
)rawliteral";

void writeServo(int ch, int angle) {
  angle = constrain(angle, HARD_MIN, HARD_MAX);
  ledcWrite(ch, map(angle, 0, 180, 1638, 8192));
}

void setSteering(float steer) {
  steer = constrain(steer, -1.0f, 1.0f);
  int d = (int)(steer * MAX_DELTA);
  writeServo(CH_SERVO_LF, CENTER + trimLF + d);
  writeServo(CH_SERVO_RF, CENTER + trimRF + d);
  writeServo(CH_SERVO_LB, CENTER + trimLB - d);
  writeServo(CH_SERVO_RB, CENTER + trimRB - d);
}

void setSpin(float val) {
  writeServo(CH_SERVO_LF, CENTER + trimLF + 45);
  writeServo(CH_SERVO_RF, CENTER + trimRF - 45);
  writeServo(CH_SERVO_LB, CENTER + trimLB - 45);
  writeServo(CH_SERVO_RB, CENTER + trimRB + 45);
  int pwm = (int)(fabs(val) * 255);
  if (val < 0) {
    ledcWrite(CH_MA_RPWM, 0);   ledcWrite(CH_MA_LPWM, pwm);
    ledcWrite(CH_MB_RPWM, 0);   ledcWrite(CH_MB_LPWM, pwm);
  } else {
    ledcWrite(CH_MA_RPWM, pwm); ledcWrite(CH_MA_LPWM, 0);
    ledcWrite(CH_MB_RPWM, pwm); ledcWrite(CH_MB_LPWM, 0);
  }
}

void setMotor(float throttle) {
  throttle = constrain(throttle, -1.0f, 1.0f);
  int pwm = (int)(fabs(throttle) * 255);
  if (throttle > 0.05f) {
    ledcWrite(CH_MA_RPWM, 0);   ledcWrite(CH_MA_LPWM, pwm);
    ledcWrite(CH_MB_RPWM, pwm); ledcWrite(CH_MB_LPWM, 0);
  } else if (throttle < -0.05f) {
    ledcWrite(CH_MA_RPWM, pwm); ledcWrite(CH_MA_LPWM, 0);
    ledcWrite(CH_MB_RPWM, 0);   ledcWrite(CH_MB_LPWM, pwm);
  } else {
    stopMotors();
  }
}

void stopMotors() {
  ledcWrite(CH_MA_RPWM, 0); ledcWrite(CH_MA_LPWM, 0);
  ledcWrite(CH_MB_RPWM, 0); ledcWrite(CH_MB_LPWM, 0);
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);

  ledcSetup(CH_MA_RPWM, MOTOR_FREQ, MOTOR_RES); ledcAttachPin(MA_RPWM_PIN, CH_MA_RPWM);
  ledcSetup(CH_MA_LPWM, MOTOR_FREQ, MOTOR_RES); ledcAttachPin(MA_LPWM_PIN, CH_MA_LPWM);
  pinMode(MA_REN_PIN, OUTPUT); digitalWrite(MA_REN_PIN, HIGH);
  pinMode(MA_LEN_PIN, OUTPUT); digitalWrite(MA_LEN_PIN, HIGH);

  ledcSetup(CH_MB_RPWM, MOTOR_FREQ, MOTOR_RES); ledcAttachPin(MB_RPWM_PIN, CH_MB_RPWM);
  ledcSetup(CH_MB_LPWM, MOTOR_FREQ, MOTOR_RES); ledcAttachPin(MB_LPWM_PIN, CH_MB_LPWM);
  pinMode(MB_REN_PIN, OUTPUT); digitalWrite(MB_REN_PIN, HIGH);
  pinMode(MB_LEN_PIN, OUTPUT); digitalWrite(MB_LEN_PIN, HIGH);

  stopMotors();

  ledcSetup(CH_SERVO_LB, SERVO_FREQ, SERVO_RES); ledcAttachPin(SERVO_LB_PIN, CH_SERVO_LB);
  ledcSetup(CH_SERVO_LF, SERVO_FREQ, SERVO_RES); ledcAttachPin(SERVO_LF_PIN, CH_SERVO_LF);
  ledcSetup(CH_SERVO_RF, SERVO_FREQ, SERVO_RES); ledcAttachPin(SERVO_RF_PIN, CH_SERVO_RF);
  ledcSetup(CH_SERVO_RB, SERVO_FREQ, SERVO_RES); ledcAttachPin(SERVO_RB_PIN, CH_SERVO_RB);
  setSteering(0.0f);

  Serial.println("\n=== ROBOT CAR BOOT ===");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 8000) {
    delay(300); Serial.print(".");
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[OK] DA KET NOI WIFI");
    Serial.print(">>> http://"); Serial.println(WiFi.localIP());
    digitalWrite(LED_PIN, HIGH);
  } else {
    WiFi.mode(WIFI_AP);
    WiFi.softAP(AP_SSID, AP_PASSWORD);
    Serial.println("\n[AP] WiFi: RobotCar | Pass: 12345678");
    Serial.print(">>> http://"); Serial.println(WiFi.softAPIP());
    for (int i = 0; i < 6; i++) { digitalWrite(LED_PIN, !digitalRead(LED_PIN)); delay(150); }
    digitalWrite(LED_PIN, HIGH);
  }

  server.on("/",        HTTP_GET,  handleRoot);
  server.on("/control", HTTP_POST, handleControl);
  server.on("/stop",    HTTP_GET,  handleStop);
  server.on("/trim",    HTTP_POST, handleTrim);
  server.begin();
  Serial.println("Web server san sang!");
}

void loop() {
  server.handleClient();
  if (millis() - lastCmd > TIMEOUT && lastCmd > 0) stopMotors();
}

void handleRoot() { server.send_P(200, "text/html", INDEX_HTML); }

void handleControl() {
  if (!server.hasArg("plain")) { server.send(400); return; }
  StaticJsonDocument<256> doc;
  if (deserializeJson(doc, server.arg("plain"))) { server.send(400); return; }
  float steer    = doc["steer"]    | 0.0f;
  float throttle = doc["throttle"] | 0.0f;
  float spin     = doc["spin"]     | 0.0f;
  lastCmd = millis();
  Serial.printf("CMD s=%.2f t=%.2f sp=%.2f\n", steer, throttle, spin);
  const float DZ = 0.1f;
  if (fabs(spin) > DZ && fabs(throttle) < DZ && fabs(steer) < DZ) {
    setSpin(spin);
  } else {
    if (fabs(steer)    < DZ) steer    = 0;
    if (fabs(throttle) < DZ) throttle = 0;
    setSteering(steer);
    setMotor(throttle);
  }
  server.send(200, "application/json", "{\"ok\":true}");
}

void handleStop() { stopMotors(); setSteering(0); server.send(200, "text/plain", "stopped"); }

void handleTrim() {
  if (!server.hasArg("plain")) { server.send(400); return; }
  StaticJsonDocument<128> doc;
  if (deserializeJson(doc, server.arg("plain"))) { server.send(400); return; }
  trimLF = doc["lf"] | trimLF;
  trimRF = doc["rf"] | trimRF;
  trimLB = doc["lb"] | trimLB;
  trimRB = doc["rb"] | trimRB;
  setSteering(0);
  server.send(200, "application/json", "{\"ok\":true}");
}