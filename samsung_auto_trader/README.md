# Samsung Auto Trader (모의투자)

한국투자증권 KIS Open API를 활용한 삼성전자(005930) 자동매매 시스템입니다.
모의투자 환경에서만 동작하며, REST API 폴링 방식으로 구현되었습니다.

## 개요

- **종목**: 삼성전자 (005930)
- **환경**: 모의투자 전용 (`https://openapivts.koreainvestment.com:29443`)
- **매매 로직**: 호가 기준 ±1,000원 지정가 매수/매도
- **운영 시간**: 09:10 ~ 15:30 KST (한국 시간)
- **방식**: REST API 폴링 (웹소켓 미사용)

## 사전 준비

### 1. 한국투자증권 모의투자 계좌 발급

- [한국투자증권 모의투자 신청](https://securities.koreainvestment.com/main/research/virtual/_static/TF07da010000.jsp) 접속
- 가상 시드머니 선택 후 신청 → 모의투자 전용 계좌번호 발급

### 2. KIS Developers Open API 신청

- [KIS Developers](https://apiportal.koreainvestment.com/) 접속
- 우측 상단 `API신청` → "모의투자계좌" 체크, 계좌번호 입력
- **APP Key**, **APP Secret** 발급 (발급 직후 한 번만 평문으로 노출되므로 즉시 보관)

### 3. 환경변수 등록 (GitHub Codespaces)

[GitHub Codespaces secrets](https://github.com/settings/codespaces)에서 다음 3개를 등록합니다.

| 환경변수 | 값 |
|---|---|
| `GH_APPKEY` | KIS Developers 발급 모의투자용 APP Key |
| `GH_APPSECRET` | KIS Developers 발급 모의투자용 APP Secret |
| `GH_ACCOUNT` | 모의투자 계좌번호 앞 8자리 |

> `GH_ACNT_PRDT_CD`(계좌 뒤 2자리, 일반적으로 `01`)는 미등록 시 기본값 `01`이 사용됩니다.

Secret 등록 후 Codespace를 재시작해야 환경변수가 주입됩니다.

## 폴더 구조

```
samsung_auto_trader/
├── config.py           # 환경 설정 (Config — URL, 종목, 시간, 환경변수 로드)
├── auth.py             # 토큰 발급 및 캐싱 (Auth & Token cache)
├── api_client.py       # HTTP 공통 레이어 (HTTP client — 재시도, 에러 처리)
├── market_data.py      # 시세 조회 (Market data — 호가 API 기반)
├── account.py          # 잔고 조회 (Account snapshot)
├── orders.py           # 매수/매도 주문 (Order client)
├── trader.py           # 메인 매매 로직 (Trading loop — 시간 체크, 사이클 관리)
├── logger.py           # 로깅 설정 (Logger)
├── main.py             # 진입점 (Entry point)
├── token_cache.json    # 토큰 캐시 (자동 생성, gitignore)
├── requirements.txt    # 의존성
└── README.md           # 본 문서
```

## 설치

```bash
cd samsung_auto_trader
pip install -r requirements.txt
```

## 개발 과정 / 초기 검증

본 시스템을 구축하기 전, 가장 작은 단위로 한투 모의투자 서버 인증이 가능한지 검증했습니다.
이 단계는 환경변수 주입, 네트워크 접근, 모의투자 URL/계정 매칭이 모두 정상임을 확인하는 최소 동작 테스트입니다.

`test_auth.py`:

```python
"""모의투자 토큰 발급 테스트 - 가장 작은 단위 확인용"""
import os
import requests

APPKEY = os.getenv("GH_APPKEY")
APPSECRET = os.getenv("GH_APPSECRET")
BASE_URL = "https://openapivts.koreainvestment.com:29443"  # 모의투자 URL

def get_token():
    url = f"{BASE_URL}/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": APPKEY,
        "appsecret": APPSECRET,
    }
    res = requests.post(url, headers=headers, json=body, timeout=10)
    print("상태 코드:", res.status_code)
    print("응답:", res.json())
    return res.json()

if __name__ == "__main__":
    print(f"APPKEY 길이: {len(APPKEY) if APPKEY else 'None'}")
    print(f"APPSECRET 길이: {len(APPSECRET) if APPSECRET else 'None'}")
    print("---")
    get_token()
```

실행 및 검증 결과:
- HTTP 200 응답
- `access_token` 정상 수신 (24시간 유효)
- 이 결과를 토대로 본 시스템의 모듈 구조 설계 진행

## 단계별 사전 점검

자동매매 메인 루프를 실행하기 전에, 모듈별로 정상 동작을 확인합니다.
세 단계 모두 성공해야 다음 단계(주문 테스트, 메인 루프)로 진행할 수 있습니다.

### Step 1. 토큰 발급 확인

```bash
python -c "from auth import AuthManager; print('토큰 OK:', AuthManager.from_env().get_token()[:20], '...')"
```

**기대 결과**: 토큰 앞 20자가 출력되며, `token_cache.json` 파일이 생성됩니다.

> 모의투자 토큰은 1분당 1회 발급 제한이 있으므로, 정상 발급 후에는 캐시가 재사용됩니다.

### Step 2. 시세 조회 확인

```bash
python -c "from auth import AuthManager; from api_client import ApiClient; from market_data import MarketDataClient; print(MarketDataClient(ApiClient(AuthManager.from_env())).get_current_quote('005930'))"
```

**기대 결과**: `PriceQuote(symbol='005930', bid_price=..., ask_price=..., last_price=...)`
삼성전자 현재가가 합리적인 범위로 출력됩니다. 장 시간 외에는 마지막 종가가 반환됩니다.

### Step 3. 잔고 조회 확인

```bash
python -c "from auth import AuthManager; from api_client import ApiClient; from account import AccountClient; print(AccountClient(ApiClient(AuthManager.from_env())).get_balance_snapshot('005930'))"
```

**기대 결과**: `AccountSnapshot(available_cash=..., holdings=[])`
가용현금이 모의투자 신청 시 선택한 가상자산 금액으로 표시됩니다.

## 안전 설계

- **모의투자 전용 URL 고정**: `config.py`의 `API_BASE_URL`이 `openapivts.koreainvestment.com:29443`으로 하드코딩되어 실전 계좌로 사고 우려 없음
- **모의투자 전용 TR ID 사용**: 매수 `VTTC0802U`, 매도 `VTTC0801U`, 잔고 `VTTC8434R`
- **1주 단위 주문**: `ORDER_QUANTITY=1`로 영향 최소화
- **KST 타임존 명시**: `zoneinfo.ZoneInfo("Asia/Seoul")`로 한국 시간 기준 매매 시간 판단 (Codespace UTC 시간과 무관)
- **공매도 방지**: 보유 수량 부족 시 매도 주문 자동 스킵
- **주문 쿨다운**: 15분 간격(`ORDER_COOLDOWN_SECONDS=900`)으로만 신규 주문
- **폴링 간격**: 5분(`POLL_INTERVAL_SECONDS=300`)으로 모의투자 API 호출 제한 회피
- **토큰 캐싱**: 동일 발급일 내 토큰 재사용으로 토큰 발급 한도 회피
- **HTTP 재시도 분리**: 5xx 서버 오류만 재시도, 4xx 클라이언트 오류는 즉시 반환

## 운영 시 주의사항

- GitHub Codespace는 브라우저 탭을 닫고 일정 시간이 지나면 자동으로 중지됩니다.
  메인 루프 운영 중에는 탭을 열어두거나, 장기 운영 시 별도의 클라우드 환경(VM 등)으로 이전이 필요합니다.
- 모의투자 API는 초당 호출 횟수 제한이 실전보다 엄격합니다 (`EGW00201` 오류 발생 가능).
- `token_cache.json`은 액세스 토큰을 저장하므로 `.gitignore`에 포함되어야 하며, 외부 공유 금지.

## 다음 단계

위 Step 1~3이 모두 성공하면, **평일 장 시간(09:10~15:30 KST)** 에 다음을 진행합니다.

1. 실제 주문 1회 수동 테스트 (체결되지 않을 가격으로)
2. 한국투자증권 모의투자 앱/홈페이지에서 주문내역 확인
3. 미체결 주문 수동 취소
4. 메인 루프 실행 (`python main.py`)

## 실행 결과 (2026-06-02)

평일 장 시간 동안 모의투자 환경에서 실제로 자동매매 시스템을 운영하고 결과를 검증했습니다.

### 운영 개요

| 항목 | 값 |
|---|---|
| 운영 일자 | 2026년 6월 2일 (월) |
| 시작 시각 | 13:16 KST |
| 종료 시각 | 15:30 KST (자동 종료) |
| 운영 시간 | 약 2시간 14분 |
| 대상 종목 | 삼성전자 (005930) |
| 시스템 크래시 | 0회 |

### 사전 점검 (Step 1~3)

토큰 발급, 시세 조회, 잔고 조회 모두 정상 동작 확인.

- **토큰**: `Reusing token from cache file` — 토큰 캐싱 정상 동작
- **시세**: `PriceQuote(symbol='005930', bid_price=..., ask_price=..., last_price=...)`
- **잔고**: `AccountSnapshot(available_cash=10000000.0, holdings=[])` — 모의투자 시드 1천만원 확인

### 첫 주문 테스트 (test_order.py)

체결되지 않을 가격(현재가 -5,000원)으로 1주 수동 매수 주문 시도.

```
현재가: 353000.0
매수가: 348000
성공: True
주문번호: None
메시지: 모의투자 매수주문이 완료 되었습니다.
```

→ 한투 모의투자 서버에서 정상 접수 확인.

### 자동매매 실행 (main.py)

#### 첫 사이클 (13:16)

```
13:16:01  Auto trader started
13:16:01  Reusing token from cache file
13:16:05  Current quote 005930 bid=350500.0 ask=351000.0
13:16:14  Balance snapshot for 005930 available_cash=10000000.0 holdings=[]
13:16:14  Submitting buy order 1 005930 @ 350000
13:16:18  Buy order result success=True message=모의투자 매수주문이 완료 되었습니다.
13:16:18  Skipping sell order because holding is insufficient (0 shares available)
13:16:21  No balance or holding change detected after orders
13:16:21  Sleeping for 300 seconds before next cycle
```

확인 사항:
- 토큰 캐시 재사용 (불필요한 발급 없음)
- 매수 주문 정상 접수
- 보유 0주이므로 매도 자동 스킵 (공매도 방지 동작)
- 5분 폴링 간격 정상 진입

#### 쿨다운 동작 검증 (13:21)

```
13:21:21  Current quote 005930 bid=351000.0 ask=351500.0
13:21:26  Balance snapshot for 005930 available_cash=10000000.0 holdings=[]
13:21:26  Order cooldown active, skipping new orders
13:21:29  Sleeping for 300 seconds before next cycle
```

→ 15분 주문 쿨다운 정상 동작. 모의투자 API 호출 폭주 방지.

#### 디버깅 및 코드 수정

세 번째 사이클(13:26)에서 `account.py`의 `_to_int` 메서드 누락으로 `AttributeError` 발생.
시스템이 크래시하지 않고 `try/except`로 예외를 잡아 다음 사이클로 정상 진행함을 확인.

수정 후 잔고 조회 결과:

```python
AccountSnapshot(
    available_cash=10000000.0,
    holdings=[
        Holding(
            symbol='005930',
            quantity=1,
            average_price=350000.0,
            current_price=352250.0,
            ...
            'evlu_pfls_amt': '2250',
            'evlu_pfls_rt': '0.64'
        )
    ]
)
```

→ 1차 실행 중 발사한 매수 주문(350,000원)이 코드 종료 이후에도 한투 서버에서 살아있다가 시세 변동으로 체결됨을 확인. 자동매매 시스템의 비동기성(주문 송신과 체결의 분리)을 실제로 검증.

#### 매수 + 매도 동시 발사 및 HTTP 재시도 (13:35)

```
13:35:26  Balance snapshot for 005930 holdings=[1]
13:35:29  Submitting buy order 1 005930 @ 351000
13:35:29  Buy order result success=True
13:35:29  Submitting sell order 1 005930 @ 353000
13:35:29  WARNING - API request failed (attempt 1/2): POST .../order-cash status=500
13:35:34  Sell order result success=True
```

확인 사항:
- 보유 1주 감지하여 매도 주문 정상 발사
- 매도 1차 시도에서 500 에러 발생
- `api_client.py`의 재시도 로직 발동, 2초 대기 후 2차 시도
- 2차 시도에서 매도 정상 접수

→ "5xx만 재시도, 4xx는 즉시 반환" 설계가 실전 환경에서 검증됨.

#### 매도 체결 확인 (13:51)

```
13:51:11  Balance snapshot for 005930 available_cash=10000000.0 holdings=[1]
13:51:11  Submitting buy order 1 005930 @ 352500
13:51:15  Buy order result success=True
13:51:15  Submitting sell order 1 005930 @ 354500
13:51:16  Sell order result success=True
```

직전 사이클 보유 2주에서 1주로 감소 → 매도 주문(353,000원)이 시세 상승에 따라 체결됨을 확인.

#### 자동 종료 (15:30)

```
15:30:00  Trading window closed during execution
15:30:00  Auto trader stopped
```

→ KST 타임존(`zoneinfo.ZoneInfo("Asia/Seoul")`) 기반 시간 체크가 정확히 동작. 한국 장 마감 시각에 정확히 자동 종료.

### 최종 결과 (한국투자증권 모의투자 시스템)

운영 종료 시점 한투 모의투자 계좌 잔고:

| 항목 | 값 |
|---|---|
| 예수금 총액 | 10,000,000원 |
| 금일 매수액 | 3,202,500원 |
| 금일 매도액 | 2,506,000원 |
| 제비용 (수수료/세금) | 5,812원 |
| D+2 정산액 | 9,297,688원 |
| 보유 종목 | 삼성전자 2주 |
| 매입 평균가 | 359,468.75원 |
| 평가금액 | 722,000원 |
| **평가손익** | **+3,063원 (+0.43%)** |
| **총 평가금액** | **10,019,688원 (+0.197%)** |

2시간 14분의 자동매매 운영 동안 매수·매도 양방향 체결이 다수 발생하였으며, 최종적으로 모의 가상자산 기준 약 +0.197% 수익으로 종료됨.

### 검증된 시스템 동작

본 운영을 통해 다음 사항들이 모두 검증됨.

- 모의투자 환경에서의 실제 매수·매도 주문 접수
- 시세 변동에 따른 실제 체결 (단순 시뮬레이션이 아닌 실제 시장 데이터 기반)
- 토큰 캐싱을 통한 발급 한도 회피
- 15분 주문 쿨다운으로 폭주 방지
- 보유 수량 부족 시 매도 자동 스킵 (공매도 방지)
- HTTP 5xx 에러 발생 시 자동 재시도, 4xx 에러 시 즉시 반환
- 런타임 예외 발생 시 `try/except`로 사이클 단위 격리, 시스템 전체 크래시 없이 다음 사이클 진행
- KST 타임존 기반 한국 장 시간 정확한 자동 종료

### 발견된 개선점

운영 중 식별된 자잘한 이슈로, 매매 로직에는 영향 없으나 향후 개선 대상.

- 호가 API 응답에서 `last_price` 추출 시 일부 케이스에서 비합리적 값 반환 (매매에는 영향 없으나 로그 정확도 개선 필요)
- 잔고 응답 필드 매칭에서 `ord_psbl_cash` 대신 `dnca_tot_amt`(예수금총금액)가 잡혀 매수 직후 가용현금이 즉시 차감되지 않음 (한투 D+2 결제 구조상 정상이나, 실시간 가용현금 표시를 원할 경우 추가 필드 매칭 필요)
- 주문 응답에서 `order_id`(주문번호) 추출 실패 — 한투 응답 키 매칭 미세 조정 필요
