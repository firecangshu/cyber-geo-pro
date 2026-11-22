#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO 客户端两段式（官方 A2M）本地验证：起假服务端，跑 probe → 402 → complete → 200。

只验证客户端与协议形态，不碰真实服务端与真实支付。
"""
import base64
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
CLIENT = os.path.join(HERE, "geo_api_client.py")
PY = sys.executable
FAIL = []


def check(cond, msg):
    print(("  [OK] " if cond else "  [FAIL] ") + msg)
    if not cond:
        FAIL.append(msg)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


STATE = {"requests": [], "bill_issued": False}


def make_bill():
    payload = {
        "protocol": {"out_trade_no": "GEOTEST20261023001", "amount": "4.99",
                     "currency": "CNY", "resource_id": "/v1/diagnose",
                     "pay_before": "2026-10-23T07:00:00+00:00",
                     "seller_signature": "ZmFrZXNpZ25hdHVyZQ==",
                     "seller_sign_type": "RSA2",
                     "seller_unique_id": "TEST_SELLER_UNIQUE_ID"},
        "method": {"seller_name": "赛博GEO", "seller_id": "TEST_SELLER_ID",
                   "seller_app_id": "TEST_SELLER_APP_ID", "goods_name": "GEO诊断",
                   "seller_unique_id_key": "seller_id", "service_id": "API_TEST_001"},
    }
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


class Fake(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else b""
        proof = self.headers.get("Payment-Proof") or ""
        STATE["requests"].append({"body": body.decode("utf-8"), "proof": proof,
                                  "ct": self.headers.get("Content-Type", "")})
        if not proof:
            # 无凭证 → 402 + Payment-Needed
            bill = make_bill()
            STATE["bill_issued"] = True
            out = json.dumps({"ok": False, "error": "PAYMENT_REQUIRED"}).encode()
            self.send_response(402)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Payment-Needed", bill)
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
            return
        if proof == "BAD_PROOF":
            out = json.dumps({"ok": False, "error": "PAYMENT_REJECTED"}).encode()
            self.send_response(402)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
            return
        # 验付通过 → 履约 → 200 + 报告
        out = json.dumps({"ok": True, "request_id": "geotest-1",
                          "diagnosis": {"score": 42, "mention_rate": 55.6},
                          "quality_gate": {"all_passed": True},
                          "fix_package": []}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


def run(args, env):
    p = subprocess.run([PY, CLIENT] + args, capture_output=True, text=True,
                       encoding="utf-8", env=env)
    out = (p.stdout or "") + (p.stderr or "")
    try:
        payload = json.loads(p.stdout)
    except Exception:
        payload = {"_raw": out[:300]}
    return p.returncode, payload, out


def main():
    port = free_port()
    srv = ThreadingHTTPServer(("127.0.0.1", port), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.3)

    env = dict(os.environ)
    env["GEO_API_ENDPOINT"] = "http://127.0.0.1:%d" % port
    env["GEO_API_TOKEN"] = "test-token"
    env["no_proxy"] = "127.0.0.1,localhost"
    env["NO_PROXY"] = "127.0.0.1,localhost"
    state = os.path.join(HERE, "_state_test")
    os.makedirs(state, exist_ok=True)

    print("=== 组 1：probe（无凭证 → 402 → 账单落盘）===")
    rc, out, raw = run(["probe", "--brand", "测试品牌", "--depth", "标准",
                        "--state-dir", state], env)
    check(rc == 7, "probe 退出码 7 = PAYMENT_REQUIRED（实际 %s）" % rc)
    check(out.get("error") == "PAYMENT_REQUIRED", "错误码 PAYMENT_REQUIRED")
    check("payment_needed" not in raw, "stdout 不含账单原文（支付指令不落日志）")
    bill_file = out.get("bill_file") or ""
    check(bool(bill_file) and os.path.exists(bill_file), "账单文件已落盘")
    check((out.get("bill") or {}).get("amount") == "4.99", "账单摘要含金额")
    check(bool((out.get("bill") or {}).get("out_trade_no")), "账单摘要含订单号")
    req_file = out.get("request_file") or ""
    check(bool(req_file) and os.path.exists(req_file), "原始请求体已落盘（供一致重放）")

    print("\n=== 组 2：complete（无凭证 → 拒绝，不交付）===")
    rc, out, _ = run(["complete", "--brand", "测试品牌", "--state-dir", state], env)
    check(rc == 3, "缺凭证 → 退出码 3（实际 %s）" % rc)
    check(out.get("error") == "MISSING_PAYMENT_PROOF", "提示缺 Payment-Proof")

    print("\n=== 组 3：complete（伪造凭证 → 402，不交付）===")
    proof_path = os.path.join(state, "payment-proof.txt")
    with open(proof_path, "w", encoding="utf-8") as fh:
        fh.write("BAD_PROOF")
    rc, out, _ = run(["complete", "--brand", "测试品牌", "--state-dir", state,
                      "--payment-proof-file", proof_path], env)
    check(rc == 7, "伪造凭证 → 退出码 7（实际 %s）" % rc)
    check(out.get("error") == "PAYMENT_REQUIRED", "错误码 PAYMENT_REQUIRED")
    check("diagnosis" not in json.dumps(out), "伪造凭证不返回任何诊断内容")

    print("\n=== 组 4：complete（有效凭证 → 200 + 报告）===")
    with open(proof_path, "w", encoding="utf-8") as fh:
        fh.write("GOOD_PROOF")
    rc, out, _ = run(["complete", "--brand", "测试品牌", "--state-dir", state,
                      "--payment-proof-file", proof_path], env)
    check(rc == 0, "有效凭证 → 退出码 0（实际 %s）" % rc)
    check(out.get("ok") is True, "返回 ok=true")
    check(bool(out.get("diagnosis")), "返回诊断数据")
    check((out.get("quality_gate") or {}).get("all_passed") is True, "返回质量门禁结果")

    print("\n=== 组 5：协议形态（body 一致 / 凭证走头不走 body）===")
    check(len(STATE["requests"]) >= 3, "服务端收到 %d 次请求" % len(STATE["requests"]))
    bodies = {r["body"] for r in STATE["requests"]}
    check(len(bodies) == 1, "所有请求 body 完全一致（重放一致性）")
    check(all("payment_token" not in r["body"] for r in STATE["requests"]),
          "body 不含 payment_token（旧形态已清除）")
    check(all("payment_proof" not in r["body"].lower() for r in STATE["requests"]),
          "body 不含凭证（凭证走请求头）")
    check(any(r["proof"] == "GOOD_PROOF" for r in STATE["requests"]),
          "Payment-Proof 走请求头")

    print("\n=== 组 6：mock 模式仍可用 ===")
    env2 = dict(env)
    env2["GEO_API_MOCK"] = "1"
    rc, out, _ = run(["probe", "--brand", "测试品牌", "--state-dir", state], env2)
    check(rc == 0, "mock probe → 0（实际 %s）" % rc)
    check(bool((out.get("report") or {}).get("diagnosis")), "mock 返回报告结构")

    srv.shutdown()
    import shutil
    shutil.rmtree(state, ignore_errors=True)
    print("\n" + ("ALL PASS ✅" if not FAIL else "FAILED %d 项 ❌\n%s"
                  % (len(FAIL), "\n".join(FAIL))))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
