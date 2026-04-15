"""
Vercel Serverless Function — 韩国投资者海外股票 TOP5 报告
GET /              → HTML 页面（带日期选择器）
GET /?start=...&end=...  → JSON 数据（Accept: application/json）
"""

import json
import sys
import os
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from http.server import BaseHTTPRequestHandler
from main import fetch_week, last_week_range
from stock_names import format_display


def generate_report(start, end, market=None):
    start_fmt = f"{start[:4]}-{start[4:6]}-{start[6:]}"
    end_fmt = f"{end[:4]}-{end[4:6]}-{end[6:]}"

    markets = [("US", "美股"), ("HK", "港股")]
    if market:
        markets = [(m, l) for m, l in markets if m == market.upper()]

    report = {
        "period": f"{start_fmt} ~ {end_fmt}",
        "source": "한국예탁결제원 (KSD) SEIBro",
        "markets": [],
    }

    for country, label in markets:
        df = fetch_week(country, start, end)
        if df.empty:
            report["markets"].append({"market": label, "code": country, "data": None})
            continue

        def make_row(r):
            ticker, cn_name = format_display(r["KOR_SECN_NM"], is_hk=(country == "HK"))
            return {
                "name": r["KOR_SECN_NM"],
                "ticker": ticker,
                "cn_name": cn_name,
                "buy": round(r["buy"]),
                "sell": round(r["sell"]),
                "net": round(r["net"]),
            }

        top_buy = df.sort_values("net", ascending=False).head(5).apply(make_row, axis=1).tolist()
        top_sell = df.sort_values("net", ascending=True).head(5).apply(make_row, axis=1).tolist()

        report["markets"].append({
            "market": label,
            "code": country,
            "weekly_net": round(df["net"].sum()),
            "top_buy": top_buy,
            "top_sell": top_sell,
        })

    return report


PAGE_HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>韩国人买什么 — 서학개미 레이더</title>
<style>
  :root{--bg:#0a0a0a;--s:#141414;--s2:#1c1c1c;--bd:#262626;--t:#e5e5e5;--t2:#a3a3a3;
    --g:#22c55e;--r:#ef4444;--a:#3b82f6}
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",sans-serif;
    background:var(--bg);color:var(--t);min-height:100vh}
  .wrap{max-width:960px;margin:0 auto}
  .hd{padding:32px 24px 24px}
  .hd .badge{display:inline-block;font-size:11px;font-weight:600;color:var(--t2);
    background:var(--s2);border:1px solid var(--bd);border-radius:6px;padding:3px 8px;
    margin-bottom:10px;letter-spacing:.5px}
  .hd h1{font-size:28px;font-weight:700;letter-spacing:-.5px;margin-bottom:6px}
  .hd .sub{font-size:14px;color:var(--t2)}
  .ctl{padding:0 24px 20px;display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end}
  .fd{display:flex;flex-direction:column;gap:4px}
  .fd label{font-size:11px;color:var(--t2);font-weight:500;text-transform:uppercase;letter-spacing:.5px}
  .fd input,.fd select{background:var(--s);border:1px solid var(--bd);color:var(--t);
    border-radius:8px;padding:8px 12px;font-size:14px;outline:none;transition:border-color .15s}
  .fd input:focus{border-color:var(--a)}
  .btn{background:var(--a);color:#fff;border:none;border-radius:8px;padding:9px 20px;
    font-size:14px;font-weight:600;cursor:pointer;transition:opacity .15s;white-space:nowrap}
  .btn:hover{opacity:.85}.btn:disabled{opacity:.4;cursor:not-allowed}
  .pre{display:flex;gap:6px;align-items:flex-end;flex-wrap:wrap}
  .pr{background:var(--s2);color:var(--t2);border:1px solid var(--bd);border-radius:6px;
    padding:6px 10px;font-size:12px;cursor:pointer;transition:all .15s;white-space:nowrap}
  .pr:hover{border-color:var(--t2);color:var(--t)}
  .pr.on{border-color:var(--a);color:var(--a);background:rgba(59,130,246,.08)}
  .ct{padding:0 24px 40px}
  .ld{text-align:center;padding:60px 20px;color:var(--t2)}
  .sp{width:28px;height:28px;border:2.5px solid var(--bd);border-top-color:var(--a);
    border-radius:50%;animation:spin .7s linear infinite;margin:0 auto 14px}
  @keyframes spin{to{transform:rotate(360deg)}}
  .em{text-align:center;padding:60px 20px;color:var(--t2);font-size:15px}
  .mc{background:var(--s);border:1px solid var(--bd);border-radius:12px;margin-bottom:20px;overflow:hidden}
  .mh{padding:16px 20px;display:flex;justify-content:space-between;align-items:center;
    border-bottom:1px solid var(--bd)}
  .mt{font-size:18px;font-weight:700;display:flex;align-items:center;gap:8px}
  .mn{font-size:15px;font-weight:600;font-variant-numeric:tabular-nums}
  .sec{padding:12px 0}
  .sl{padding:0 20px 8px;font-size:12px;font-weight:600;text-transform:uppercase;
    letter-spacing:.5px;display:flex;align-items:center;gap:6px}
  .dot{width:6px;height:6px;border-radius:50%}
  .sr{display:flex;align-items:center;justify-content:space-between;padding:10px 20px;transition:background .1s}
  .sr:hover{background:var(--s2)}
  .sl2{display:flex;align-items:center;gap:10px;min-width:0;flex:1}
  .bar{width:3px;height:32px;border-radius:2px;flex-shrink:0}
  .si{min-width:0}
  .stk{font-size:16px;font-weight:700;letter-spacing:-.3px}
  .scn{font-size:12px;color:var(--t2);margin-left:6px;font-weight:400}
  .sn{font-size:11px;color:#525252;margin-top:1px;white-space:nowrap;overflow:hidden;
    text-overflow:ellipsis;max-width:320px}
  .srt{text-align:right;flex-shrink:0}
  .snet{font-size:17px;font-weight:700;font-variant-numeric:tabular-nums;letter-spacing:-.5px}
  .sd{font-size:11px;color:#525252;margin-top:2px;font-variant-numeric:tabular-nums}
  .dv{height:1px;background:var(--bd);margin:0 20px}
  .ft{text-align:center;padding:20px;font-size:11px;color:#404040}
  @media(max-width:640px){
    .hd h1{font-size:22px}.ctl{flex-direction:column}.sn{max-width:180px}
  }
</style>
</head>
<body>
<div class="wrap">
  <div class="hd">
    <div class="badge">서학개미 레이더</div>
    <h1>韩国人买什么</h1>
    <p class="sub">한국예탁결제원(KSD) 해외주식 결제 데이터</p>
  </div>
  <div class="ctl">
    <div class="fd"><label>开始日期</label><input type="date" id="sd"></div>
    <div class="fd"><label>结束日期</label><input type="date" id="ed"></div>
    <button class="btn" id="lb" onclick="go()">查询</button>
    <div class="pre" id="ps"></div>
  </div>
  <div class="ct" id="ct"><div class="em">选择日期范围后点击「查询」</div></div>
  <div class="ft">数据来自한국예탁결제원(KSD)官方结算数据，仅供参考，不构成投资建议。</div>
</div>
<script>
function D(d){return d.toISOString().slice(0,10)}
function init(){
  var ps=document.getElementById('ps'),t=new Date(),f=new Date(t);
  while(f.getDay()!==5)f.setDate(f.getDate()-1);
  for(var i=0;i<4;i++){
    var e=new Date(f);e.setDate(e.getDate()-7*i);
    var s=new Date(e);s.setDate(s.getDate()-4);
    var lb=i===0?'本周':i===1?'上周':(i+1)+'周前';
    var b=document.createElement('button');b.className='pr';b.textContent=lb;
    b.dataset.s=D(s);b.dataset.e=D(e);
    b.onclick=(function(b){return function(){
      document.getElementById('sd').value=b.dataset.s;
      document.getElementById('ed').value=b.dataset.e;
      document.querySelectorAll('.pr').forEach(function(p){p.classList.remove('on')});
      b.classList.add('on');go();
    }})(b);
    ps.appendChild(b);
    if(i===1){
      document.getElementById('sd').value=D(s);
      document.getElementById('ed').value=D(e);
      b.classList.add('on');
    }
  }
}
function $(v){
  var a=Math.abs(v);
  if(a>=1e9)return'$'+(a/1e9).toFixed(2)+'B';
  if(a>=1e6)return'$'+(a/1e6).toFixed(1)+'M';
  if(a>=1e3)return'$'+(a/1e3).toFixed(0)+'K';
  return'$'+a.toFixed(0);
}
function S(v){return(v>=0?'+':'-')+$(v)}
function R(m){
  if(!m.top_buy){
    return'<div class="mc"><div class="mh"><div class="mt">'
      +(m.code==='US'?'\u{1F1FA}\u{1F1F8}':'\u{1F1ED}\u{1F1F0}')+' '+m.market
      +'</div></div><div style="padding:32px 20px;text-align:center;color:var(--t2)">该时段暂无数据</div></div>';
  }
  var nc=m.weekly_net>=0?'var(--g)':'var(--r)',
      fl=m.code==='US'?'\u{1F1FA}\u{1F1F8}':'\u{1F1ED}\u{1F1F0}';
  function rows(items,buy){
    return items.map(function(it){
      var n=buy?it.net:-it.net,c=buy?'var(--g)':'var(--r)',
          cn=it.cn_name?'<span class="scn">'+it.cn_name+'</span>':'';
      return'<div class="sr"><div class="sl2"><div class="bar" style="background:'+c+'"></div>'
        +'<div class="si"><div><span class="stk">'+it.ticker+'</span>'+cn+'</div>'
        +'<div class="sn">'+it.name+'</div></div></div>'
        +'<div class="srt"><div class="snet" style="color:'+c+'">'+S(n)+'</div>'
        +'<div class="sd">买入 '+$(it.buy)+' / 卖出 '+$(it.sell)+'</div></div></div>';
    }).join('');
  }
  return'<div class="mc"><div class="mh"><div class="mt">'+fl+' '+m.market+'</div>'
    +'<div class="mn" style="color:'+nc+'">周净买入 '+S(m.weekly_net)+'</div></div>'
    +'<div class="sec"><div class="sl" style="color:var(--g)"><div class="dot" style="background:var(--g)"></div>TOP 净买入 (NET BUY)</div>'
    +rows(m.top_buy,true)+'</div><div class="dv"></div>'
    +'<div class="sec"><div class="sl" style="color:var(--r)"><div class="dot" style="background:var(--r)"></div>TOP 净卖出 (NET SELL)</div>'
    +rows(m.top_sell,false)+'</div></div>';
}
async function go(){
  var sv=document.getElementById('sd').value,ev=document.getElementById('ed').value;
  if(!sv||!ev)return;
  var s=sv.replace(/-/g,''),e=ev.replace(/-/g,''),
      ct=document.getElementById('ct'),b=document.getElementById('lb');
  ct.innerHTML='<div class="ld"><div class="sp"></div>正在从 KSD 获取数据...</div>';
  b.disabled=true;b.textContent='加载中...';
  try{
    var r=await fetch('/api?start='+s+'&end='+e,{headers:{'Accept':'application/json'}});
    var d=await r.json();
    if(!d.markets||d.markets.length===0){ct.innerHTML='<div class="em">暂无数据</div>';}
    else{ct.innerHTML='<div style="font-size:13px;color:var(--t2);margin-bottom:16px">结算日: '
      +d.period+'</div>'+d.markets.map(R).join('');}
  }catch(ex){ct.innerHTML='<div class="em" style="color:var(--r)">加载失败: '+ex.message+'</div>';}
  finally{b.disabled=false;b.textContent='查询';}
}
init();
</script>
</body>
</html>"""


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        start = params.get("start", [None])[0]
        end = params.get("end", [None])[0]
        accept = self.headers.get("Accept", "")

        if start and end and "application/json" in accept:
            market = params.get("market", [None])[0]
            data = generate_report(start, end, market)
            body = json.dumps(data, ensure_ascii=False, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "s-maxage=3600, stale-while-revalidate=600")
            self.end_headers()
            self.wfile.write(body)
        else:
            body = PAGE_HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "s-maxage=86400, stale-while-revalidate=3600")
            self.end_headers()
            self.wfile.write(body)
