# scripts

설치, 데이터 준비, 모델 변환, 실행, 품질 점검 등 반복 작업을 재현 가능한 스크립트로 관리합니다.

## Windows 로컬 앱 실행

저장소 루트에서 아래 한 명령을 실행하면 NAVER Maps 키를 안전하게 입력받아 FastAPI(`8000`)와 Vite(`5173`)를 함께 시작합니다. 시스템 PATH에 Node.js가 없어도 Codex 데스크톱에 포함된 Node.js를 자동으로 찾습니다. 키는 파일이나 명령행 인수에 저장하지 않으며, 실행을 종료하면 두 서버도 함께 종료됩니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local-app.ps1
```

포트가 이미 사용 중이면 해당 PID와 함께 명확히 중단합니다. 기존 개발 서버를 종료한 뒤 다시 실행하세요.
