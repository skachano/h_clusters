# 恒等分解 (RI)

!!! info "前提知識"
    [ハートリー–フォック法](hartree-fock.md)、[基底関数系](basis-sets.md)

二電子積分 $(\mu\nu|\lambda\sigma)$ はほとんどすべての手法のボトルネックである。基底関数が $N$ 個あるとその数は約 $N^4/8$ 個になる。**恒等分解** (RI、**密度フィッティング**とも呼ぶ) は、これをはるかに少ない三指数の量で近似する。精度はほとんど失われず、MP2 は数倍速くなる。このプロジェクトで MP2 による構造レベルを手の届くものにしたのがこれである。

## 考え方

二電子積分は 2 つの**対密度** $\phi_\mu\phi_\nu$ と $\phi_\lambda\phi_\sigma$ の間のクーロン反発である。RI は各対密度を、第二の**補助**基底関数系 $\{\chi_P\}$ で展開する:

$$
\phi_\mu(\mathbf{r})\phi_\nu(\mathbf{r}) \approx \sum_P c^{\mu\nu}_P\,\chi_P(\mathbf{r})
$$

クーロンエネルギーの誤差が最小になるように係数を選ぶと

$$
(\mu\nu|\lambda\sigma) \approx \sum_{PQ} (\mu\nu|P)\,\big[\mathbf{V}^{-1}\big]_{PQ}\,(Q|\lambda\sigma),
\qquad V_{PQ} = (P|Q)
$$

となる。必要なのは三指数積分 $(\mu\nu|P)$ と二指数行列 $\mathbf{V}$ だけである。補助基底は普通、軌道基底の 3〜4 倍の大きさがあるが、それでも $N^2 N_\text{aux}$ 個の数は $N^4$ よりはるかに少なく、高速な行列積で組み合わせられる。

名前は、完全系に対する数学的な恒等式 $1 = \sum_P |P\rangle\langle P|$ に由来する。RI はこれを不完全な系で使う。

### 種類

| 名前 | 近似するもの | 補助基底 |
|---|---|---|
| RI-J | フォック行列のクーロン部分 | `/J` 系 (def2/J) |
| RI-JK | クーロンと交換 | `/JK` 系 (例: aug-cc-pVTZ/JK) |
| RI-MP2 | MP2 のエネルギーと勾配に現れる積分 | `/C` 系 (例: aug-cc-pVTZ/C) |

補助基底は対応する軌道基底に合わせてつくられているので、組になっている。誤差は系統的で小さく、化学的精度よりはるかに小さい。またエネルギー差ではほぼ打ち消し合う。

## 例: L1M が RI を使う理由

フェーズ 4 の試験計算で、1 コアでの H₁₀ の MP2/aug-cc-pVTZ 勾配 (`doc/Plan.md`、フェーズ 4):

| MP2 勾配 | 時間 |
|---|---|
| 従来法、閉殻 | 200 秒 |
| 従来法、開殻 | 880 秒 |
| RI-MP2 + RI-JK | 38 秒 |

構造最適化には数十回の勾配計算が必要で、数値的な振動数計算には 1 構造あたりさらに約 60 回必要になる。5〜20 倍の差が、MP2 による構造レベルをそもそも使えるかどうかを決めた。

## h_clusters での登場箇所

- **L1M** は `worker/src/hclust/levels.py` で `RI-MP2 RIJK` とされ、基底の行は `aug-cc-pVTZ aug-cc-pVTZ/C aug-cc-pVTZ/JK` (軌道基底、次に 2 つの補助基底) である。
- ORCA 6.1 には解析的な RI-MP2 ヘッセ行列がないので、L1M の振動数は数値的に求め (`analytic_hessian=False`)、各状態の上位 3 構造だけに行う。
- CCSD(T) (L2) は RI なしで実行する。そのディスク節約型の積分アルゴリズム (`KC_AOX`) は RI 変換と組み合わせられないからである (フェーズ 4 の試験計算)。

## 参考文献

- F. Weigend, M. Häser, *Theor. Chem. Acc.* **97**, 331 (1997): RI-MP2。
- F. Weigend, *Phys. Chem. Chem. Phys.* **4**, 4285 (2002): 交換に対する RI (RI-JK) とその補助基底関数系。
- F. Jensen, *Introduction to Computational Chemistry*, 3rd ed., 積分近似の節。
