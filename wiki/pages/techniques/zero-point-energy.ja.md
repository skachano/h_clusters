# 零点エネルギー

!!! info "前提知識"
    [ポテンシャルエネルギー曲面](../foundations/potential-energy-surface.md#vibrations-and-vibrational-levels)、[振動数](frequencies.md)

絶対零度でも分子は振動している。最も低い振動準位は井戸の底より上にある。その残りのエネルギーが**零点エネルギー** (ZPE) である。ほとんどの化学では小さいが、最も軽い原子である水素では大きい。このプロジェクトの弱く結合したクラスターでは、クラスターがそもそもまとまっていられるかどうかを ZPE が決める。

## 考え方

調和近似では、振動数 $\omega_i$ の各基準振動 $i$ が量子の半分を寄与する:

$$
\text{ZPE} = \sum_{i=1}^{3N-6} \tfrac{1}{2}\hbar\omega_i
$$

したがって ZPE は[振動数計算](frequencies.md)からそのまま得られる。軽い原子は速く振動する ($\omega \propto 1/\sqrt{\mu}$) ので ZPE が大きい。[H₂](app:s/2/0/1) と D₂ の比較は [同位体の表](../foundations/born-oppenheimer.md#one-surface-for-all-isotopes)にある。

安定性にとって重要なのは、ある過程での ZPE の**変化**である。クラスターが断片に分かれると、振動の一部は断片の自由な並進や回転になり、それらには零点エネルギーがない。したがって断片を合わせた ZPE は普通クラスターの ZPE より小さく、

$$
D_0 = D_e - \Delta\text{ZPE}, \qquad
\Delta\text{ZPE} = \text{ZPE}(\text{cluster}) - \sum \text{ZPE}(\text{fragments}) > 0
$$

となる ([結合エネルギー](../foundations/potential-energy-surface.md#binding-energy-d_e-and-d_0))。

## 例: [H₅⁺](app:s/5/1/1) → [H₃⁺ + H₂](app:s/5/1/1) { #example-h5-h3-h2 }

ベースラインキャンペーンより。電子エネルギーは CCSD(T)/aug-cc-pVTZ、ZPE は RI-MP2/aug-cc-pVTZ の調和振動数から求め、どちらも MP2 構造で計算した。

| | エネルギー (ハートリー) | ZPE (ハートリー) | ZPE (eV) |
|---|---|---|---|
| [H₅⁺](app:s/5/1/1) (C₂ᵥ) | −2.527957 | 0.035458 | 0.965 |
| [H₃⁺](app:s/3/1/1) | −1.341728 | 0.020718 | 0.564 |
| [H₂](app:s/2/0/1) | −1.172615 | 0.010291 | 0.280 |

- $D_e$ = (−1.341728 − 1.172615) − (−2.527957) = 0.013614 ハートリー = **8.54 kcal/mol**
- ΔZPE = 0.035458 − (0.020718 + 0.010291) = 0.004449 ハートリー = **2.79 kcal/mol**
- $D_0$ = 8.54 − 2.79 = **5.75 kcal/mol**

結合エネルギーの 3 分の 1 が零点エネルギーに食われている。[H₅⁺](app:s/5/1/1) の 9 個のモードのうち 5 個は断片には存在しない。最もやわらかい 203 cm⁻¹ のモードは、[H₂](app:s/2/0/1) ユニットが [H₃⁺](app:s/3/1/1) に対して揺れる運動である。

## どれほど信頼できるか

調和近似の式は、どの井戸も放物線であると仮定する。これは硬い結合 ([H₂](app:s/2/0/1)、[H₃⁺](app:s/3/1/1)) にはよいが、クラスターをまとめているやわらかい運動には悪い。そこでは実際のポテンシャルが強く非調和的で、ZPE が大きな割合で外れることがある。[H₅⁺](app:s/5/1/1) では影響はさらに大きい。C₂ᵥ 構造と D₂d 構造の差はわずか 0.13 kcal/mol で ZPE よりはるかに小さいので、実際の分子はどちらの井戸にもとどまっていない。中央の陽子は 2 つの [H₂](app:s/2/0/1) ユニットの間を自由に行き来する (「流動的」である)。[原子核の量子効果](../pitfalls/quantum-nuclear-effects.md)を参照。

## [h_clusters](https://github.com/skachano/h_clusters) での登場箇所 { #where-this-appears-in-h_clusters }

- ORCA は振動数計算のたびに ZPE を報告し、それは各結果の `thermo` フィールドに (`"zpe"`、ハートリー単位で) 保存される。
- 計画では結合エネルギーを ΔE と ΔE₀ = ΔE + ΔZPE の両方で報告し、安定性の判定には $D_{0,\min} > 0$ のクラスターのための別の最上位カテゴリー `bound_with_zpe` がある (`doc/Plan.md` §2.2)。
- フェーズ 8 は調和近似の ZPE の先に進む。[H₂](app:s/2/0/1)、[H₃⁺](app:s/3/1/1)、[H₅⁺](app:s/5/1/1) には VPT2、中性クラスターには[拡散モンテカルロ法](../methods/diffusion-monte-carlo.md)を使い、調和近似の $D_0 < 0$ が誤りであることがわかった。
- [ウェブアプリ](app:): [$D_e$ の一覧](app:?q=d_e)と[$D_0$ の一覧](app:?q=d_0)を比べると、ZPE で束縛が外れるクラスターが分かる。VPT2 と DMC の研究は[「追加計算」](app:studies)ページにある。

## 参考文献

- F. Jensen, *Introduction to Computational Chemistry*, 3rd ed., 振動数と熱化学の節。
- D. A. McQuarrie, *Statistical Mechanics*: 調和振動子とその零点エネルギー。
