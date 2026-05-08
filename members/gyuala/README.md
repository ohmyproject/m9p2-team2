# DataLab 안정화 수정 사항

이번 수정은 `RemoteDisconnected('Remote end closed connection without response')` 오류를 줄이기 위한 안정화 패치입니다.

## 주요 변경

1. FastAPI 서버에서 Naver DataLab 요청을 전역 Lock으로 직렬화했습니다.
2. 요청 사이 간격을 기본 1초로 늘렸습니다.
3. 프론트엔드에서 `/api/datalab/dashboard-signals`와 `/api/datalab/ingredient-trend`를 동시에 호출하지 않고 순차 호출하도록 변경했습니다.
4. dashboard-signals와 ingredient-trend 결과를 10분 캐시하여 새로고침/업데이트 시 네이버 API를 반복 폭주 호출하지 않게 했습니다.
5. 오류 메시지를 너무 길게 나열하지 않고 요약하도록 했습니다.

## 실행

```bash
npm start
```

브라우저에서 확인:

```text
http://127.0.0.1:3000
```

상태 확인:

```text
http://127.0.0.1:3000/health
http://127.0.0.1:3000/api/datalab/status
```

## 계속 같은 오류가 나면

`.env`에서 아래 값을 조금 더 키우세요.

```env
NAVER_DATALAB_REQUEST_GAP_SECONDS=1.5
NAVER_DATALAB_BACKOFF_SECONDS=1.5
NAVER_DATALAB_MAX_RETRIES=5
```
