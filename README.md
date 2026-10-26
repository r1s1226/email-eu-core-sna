# 조직 이메일 네트워크의 핵심 인물 탐지와 부서 예측

SNAP email-Eu-core 이메일 네트워크로 조직의 핵심 인물과 부서 구조를 분석한 사회 네트워크 분석 기말 프로젝트입니다. 한양대학교 ERICA, 2026년 2학기. 팀: 당택군 · 란가성 · 왕철한 · 유열

- 결과 웹페이지: https://r1s1226.github.io/email-eu-core-sna/
- 발표 자료: [슬라이드 PDF](https://r1s1226.github.io/email-eu-core-sna/files/final-presentation.pdf) · [PowerPoint](https://r1s1226.github.io/email-eu-core-sna/files/final-presentation.pptx)

## 폴더 구성

```
pilot/pilot.py            전체 실험 코드 (그래프 통계, 중심성·clique, 핵심 인물 제거, DeepWalk·node2vec, GCN)
pilot/results/            실험 결과: pilot_results.json, 임베딩(.npy), 그림
presentation/             발표용 그림 코드(make_figures.py)와 그림(figures/)
presentation/deck/        발표 슬라이드 생성·내보내기 코드
data/download_data.py     SNAP 데이터 내려받기 (데이터 파일은 저장소에 넣지 않음)
build_data.py             웹페이지용 데이터(site_data.json) 생성
build_site.py             웹페이지(docs/index.html) 생성
docs/                     GitHub Pages: 결과 웹페이지와 발표 자료(files/)
```

## 실행 방법

Python 3.12 이상에서 저장소 최상위 폴더 기준으로 실행합니다.

```
pip install -r requirements.txt
python data/download_data.py                              # data/email-Eu-core/ 에 원본 데이터
python pilot/pilot.py data/email-Eu-core pilot/results    # 전체 실험 → pilot/results/
python presentation/make_figures.py                       # 발표용 그림, presentation/figures/removal_curves.npz
python build_data.py                                      # site_data.json
python build_site.py                                      # docs/index.html
```

- `pilot.py`는 betweenness를 여러 번 다시 계산하고 임베딩을 시드 3개로 학습하므로 시간이 꽤 걸립니다. 결과는 이미 `pilot/results/`에 들어 있어서, 그림과 웹페이지만 다시 만들 때는 이 단계를 건너뛰어도 됩니다.
- skip-gram(DeepWalk·node2vec)과 GCN은 numpy로 직접 구현해서 PyTorch 없이 돌아갑니다. 무작위 시드는 0으로 고정했습니다.
- `make_figures.py`는 한글 글꼴(맑은 고딕, 나눔고딕, Noto Sans CJK 중 하나)이 필요합니다.

### 실험 설정

- 자기 루프 642개를 지우고 무방향 그래프로 바꾼 뒤, 최대 연결 요소(LCC) 986명을 분석합니다.
- 분류는 5명 이상인 35개 부서(968명)에 층화 5-fold를 쓰고, 모든 방법에 같은 fold를 적용합니다. 지표는 정확도와 Macro-F1입니다.
- 핵심 인물 제거는 betweenness(10명마다 재계산), degree(매번 재계산), 무작위(20회 평균)를 비교합니다.

### 슬라이드 (presentation/deck)

`build_deck.py`가 슬라이드 11장(본문 8장, 부록 3장)을 `presentation/deck/project/slides/`에 HTML로 만들고, `build_exports.py`와 `make_pptx.ps1`이 PDF와 PowerPoint로 내보냅니다. 내보내기는 Windows의 Microsoft Edge와 PowerPoint를 씁니다.

```
python presentation/deck/network_png.py site_data.json presentation/deck/network_dark.png
python presentation/deck/build_deck.py site_data.json presentation/figures/removal_curves.npz presentation/deck presentation/deck/preview.html
```

## 데이터와 인용

데이터는 [SNAP email-Eu-core](https://snap.stanford.edu/data/email-Eu-core.html)입니다. 이 데이터를 쓸 때는 다음 두 논문을 인용합니다.

- J. Leskovec, J. Kleinberg, C. Faloutsos. Graph Evolution: Densification and Shrinking Diameters. ACM TKDD, 2007.
- H. Yin, A. R. Benson, J. Leskovec, D. F. Gleich. Local Higher-order Graph Clustering. KDD, 2017.

수치는 예비 실험 결과이며, 웹페이지의 "한계" 부분에 적은 조건(데이터 분할 1개, 하이퍼파라미터 튜닝 없음 등)에서 얻었습니다.
