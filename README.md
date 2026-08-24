# 자동진행단 (Auto Progress Squad)

> Intel 융합 DX 6기 팀 프로젝트 저장소

- 팀명: **자동진행단**
- 저장소: `auto-progress-squad`
- 프로젝트 기간: 2026-08-24 ~ 2026-09-09
- 발표 예정일: 2026-09-09
- 프로젝트 주제: **논의 중**
- 현재 단계: 팀 구성 및 문제 정의

## 프로젝트 목표

세 명의 팀원이 AI와 Intel 교육과정에서 배운 기술을 활용해 실제 문제를 해결하는 프로젝트를 설계하고 구현합니다.  
주제가 확정되기 전까지 특정 기술, 모델 또는 하드웨어가 결정된 것처럼 기록하지 않습니다.

## 먼저 정할 것

1. 해결할 문제와 대상 사용자
2. 입력과 기대 출력
3. 성공을 판단할 정량·정성 기준
4. 우리 팀이 직접 구현할 범위와 외부 모듈
5. 데이터·모델·하드웨어 확보 가능성
6. 세 명의 담당 영역과 공통 검증 책임

## 문서 구조

| 경로 | 용도 |
| --- | --- |
| [docs/problem-definition.md](docs/problem-definition.md) | 문제 정의, 목표, 성공 기준 |
| [docs/use-cases.md](docs/use-cases.md) | 사용자·시스템 유스케이스 |
| [docs/architecture.md](docs/architecture.md) | High Level Design 및 모듈 경계 |
| [docs/roles.md](docs/roles.md) | 역할 분담과 협업 규칙 |
| [docs/troubleshooting.md](docs/troubleshooting.md) | 오류와 해결 과정 |
| [docs/decisions](docs/decisions) | 주요 기술 의사결정 기록 |
| [src](src) | 구현 코드 |
| [tests](tests) | 자동·수동 검증 |
| [scripts](scripts) | 실행·변환·점검 스크립트 |
| [data](data) | 데이터 안내 및 소형 샘플 |
| [models](models) | 모델 출처·학습·변환 정보 |
| [presentation](presentation) | 발표 자료와 시연 순서 |

## 실행 방법

주제와 기술 스택 확정 후 아래 항목을 실제 명령으로 교체합니다.

```text
Prerequisites: TODO
Install:       TODO
Run:           TODO
Test:          TODO
```

## 프로젝트 관리

모든 작업은 가능한 한 GitHub Issue에 연결합니다.

1. Issue에서 목표와 완료 조건을 정의합니다.
2. 작업 브랜치에서 변경합니다.
3. Pull Request에 테스트 결과와 화면·로그 증거를 남깁니다.
4. 검토 후 `main`에 병합합니다.

## 평가 증거 체크

- [ ] AI 활용 주제와 문제 해결 가치
- [ ] Intel 가속기 또는 교육과정 기술 활용 근거
- [ ] High Level Design과 실제 구현의 일치
- [ ] 직접 구현 영역과 외부 모듈의 구분
- [ ] 모델 학습·변환·추론 과정 재현
- [ ] 하드웨어 입출력 또는 실환경 검증
- [ ] Milestone·Issue·PR 기반 협업 기록
- [ ] 단위 테스트·Lint·CI 실행 결과
- [ ] 발표용 정상/오류 시나리오와 복구 절차

## 참고 자료

- [이전 기수 저장소 모음](https://github.com/pskcci?tab=repositories)
- [DX-03 프로젝트 문서 템플릿](https://github.com/pskcci/DX-03/tree/main/doc/project)

## 팀원

| 이름 | GitHub | 담당 영역 |
| --- | --- | --- |
| 김도홍 | [@KIMDOHONG](https://github.com/KIMDOHONG) | 조율 예정 |
| 팀원 2 | TODO | TODO |
| 팀원 3 | TODO | TODO |
