# 이메일로 읽은 조직

SNAP email-Eu-core 이메일 네트워크로 조직의 핵심 인물과 부서 구조를 분석한 사회 네트워크 분석 기말 프로젝트의 결과 페이지입니다. 한양대학교 ERICA, 2026년 2학기.

- 페이지: `docs/index.html` 한 파일에 데이터까지 들어 있습니다. GitHub Pages에서 **Settings → Pages → Branch `main`, 폴더 `/docs`** 로 설정하면 됩니다.
- 팀: 당택군 · 란가성 · 왕철한 · 유열

## 다시 만들기

```
python build_data.py   # pilot 결과에서 site_data.json 생성 (networkx, scikit-learn 필요)
python build_site.py   # index.src.html + site_data.json → index.html, docs/index.html
```

`build_data.py`는 같은 저장소 상위 폴더의 `pilot/pilot.py`, `pilot/results/`, `발표/figures/removal_curves.npz`, `data/email-Eu-core/`를 읽습니다.

## 데이터와 인용

데이터는 [SNAP email-Eu-core](https://snap.stanford.edu/data/email-Eu-core.html)입니다. 이 데이터를 쓸 때는 다음 두 논문을 인용합니다.

- J. Leskovec, J. Kleinberg, C. Faloutsos. Graph Evolution: Densification and Shrinking Diameters. ACM TKDD, 2007.
- H. Yin, A. R. Benson, J. Leskovec, D. F. Gleich. Local Higher-order Graph Clustering. KDD, 2017.

수치는 예비 실험 결과이며, 페이지의 "한계" 부분에 적은 조건에서 얻었습니다.
