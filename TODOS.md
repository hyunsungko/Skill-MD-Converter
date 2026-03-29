# TODOS

## v2 완료 (2026-03-29)
- [x] markitdown → docling 백엔드 교체
- [x] PDF 포맷 지원 추가
- [x] 이미지 전용 PPTX fallback (LibreOffice → pdftoppm → AI 비전)
- [x] 품질 테스트 통과 (PDF, PPTX, XLSX, DOCX)
- [x] README 보강 (설치 가이드, 활용 가이드, 품질 비교)

## v3: 검토 사항
- **docling DocumentConverter 재사용:** 현재 변환할 때마다 DocumentConverter()를 새로 생성. 여러 파일 배치 변환 시 인스턴스 재사용으로 모델 로딩 시간 절약 가능.
- **OCR 언어 설정:** docling OCR 엔진의 언어 설정을 사용자가 커스터마이즈할 수 있도록 옵션 추가 검토.
- **venv 자동 감지:** docling이 venv에 설치된 경우 자동 감지하여 활성화하는 로직 추가 검토.
