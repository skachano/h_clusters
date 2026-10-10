# MP2

!!! info "前提知識"
    [ハートリー–フォック法](hartree-fock.md)

二次のメラー–プレセット摂動論 (MP2) は、[ハートリー–フォック](hartree-fock.md)計算に電子相関を加える最も安価な方法である。実際の電子間反発と HF が平均化した反発の差を小さな摂動として扱い、その主要な補正を計算する。MP2 には自己相互作用誤差がなく、分散力も含むので、このプロジェクトでは DFT と並ぶ 2 つ目の構造レベル (L1M) になっている。

## 考え方

### 摂動論

問題が解ける問題に近いときは

$$
\hat{H} = \hat{H}_0 + \lambda\hat{V}
$$

と書き、$\hat{H}_0$ は解けて $\hat{V}$ は小さいとして、エネルギーを $\lambda$ のべきで展開する: $E = E^{(0)} + E^{(1)} + E^{(2)} + \ldots$

メラーとプレセット (1934 年) は $\hat{H}_0$ として [フォック演算子](hartree-fock.md#step-2-the-mean-field)の和を選んだ。その解は HF の行列式である。すると $\hat{V}$ は、平均場が取りこぼした電子間反発の部分になる。はじめの 2 項を足すとちょうど HF のエネルギーになるので、最初の補正は二次の項になる。それが MP2 である。

### MP2 エネルギー

$E^{(2)}$ は、占有軌道 $i, j$ から空の (仮想) 軌道 $a, b$ へ 2 個の電子を移すすべての方法についての和である:

$$
E^{(2)} = \sum_{ij}^\text{occ}\sum_{ab}^\text{virt}
\frac{(ia|jb)\big[2(ia|jb) - (ib|ja)\big]}{\varepsilon_i + \varepsilon_j - \varepsilon_a - \varepsilon_b}
$$

(閉殻、空間軌道。) 各項は二電子励起であり、HF 状態とどれだけ強く結合するか (分子の積分) と、どれだけエネルギーがかかるか (分母の軌道エネルギー差) で重みづけられている。分母は負なので $E^{(2)}$ は常に負である。相関はエネルギーを下げる。

## 例: STO-3G の H₂

占有軌道が 1 つ ($\sigma_g$)、仮想軌道が 1 つ ($\sigma_u$) なので、和は 1 項だけである:

```python
--8<-- "h2_mp2_opt_freq.py:mp2"
```

R = 1.4 bohr で ([`h2_mp2_opt_freq.py`](#the-code)):

```text
Correlation energy at R = 1.4 bohr: MP2 -0.0132, FCI -0.0206 hartree (MP2 recovers 64%)
```

MP2 の値は Szabo & Ostlund と一致する。この小さな基底では、MP2 は厳密な相関エネルギーの 3 分の 2 を得る。大きな基底関数系で、平衡構造付近の分子なら、典型的にはおよそ 80〜90 % を得る。

### コード { #the-code }

??? example "実行方法とソース全体"
    ```sh
    docker run --rm -v ./wiki/examples:/ex hclust-worker:dev python /ex/h2_mp2_opt_freq.py
    ```
    ```python
    --8<-- "h2_mp2_opt_freq.py"
    ```

## 長所と短所

- **自己相互作用誤差がない。** MP2 は自己相互作用のない HF 軌道から出発する。MP2 が H₅⁺ の C₂ᵥ H₃⁺·H₂ 構造を保つのはこのためであり、このプロジェクトの DFT レベルはどれもそれを陽子共有型の D₂d 構造に変えてしまう。
- **分散力を含む。** 二電子励起は、2 つの分子上の電子の相関したゆらぎを記述する。それがまさに分散力である。MP2 は分散力をいくらか過大評価しがちである。
- **大きな基底が必要。** 相関エネルギーは基底の大きさに対してゆっくり収束する。MP2/aug-cc-p**VDZ** ではすでに H₅⁺ が D₂d に崩れ、三重ζで C₂ᵥ が保たれる (`doc/Plan.md`、フェーズ 4)。
- **伸びた結合やほぼ縮退した状態では破綻する。** 差 $\varepsilon_a + \varepsilon_b - \varepsilon_i - \varepsilon_j$ が小さくなると項が発散する。摂動論は HF がよい出発点であることを前提にしているが、[結合の切断](hartree-fock.md#bond-breaking)ではそうではない。
- **開殻:** 非制限 MP2 (UMP2) は UHF 参照の [スピン汚染](../pitfalls/spin-contamination.md)をそのまま引き継ぐ。
- **コスト:** 基底関数の数の $N^5$ で増える。[RI](resolution-of-identity.md) を使えばはるかに安くなる。

このプロジェクトの H₂ での MP2 の比較 (aug-cc-pVTZ 基底):

| | MP2 (L1M) | CCSD(T) (L2) | 厳密値 |
|---|---|---|---|
| r_e | 0.737 Å | — | 0.741 Å |
| 調和振動数 | 4517 cm⁻¹ | — | 4401 cm⁻¹ |
| エネルギー | −1.16502 ハートリー | −1.17263 | −1.17447 |

## h_clusters での登場箇所

- `worker/src/hclust/levels.py` の **L1M**: RI-JK と aug-cc-pVTZ 基底を用いる RI-MP2。昇格したすべての構造を最適化し (ステージ `mp2`)、各状態の上位 3 つに数値的な振動数計算を行う (`mp2_freq`)。ORCA 6.1 には解析的な RI-MP2 ヘッセ行列がないためである。
- 一電子の化学種 (H、H₂⁺) には相関させるものがないので、L1M はそれらに対して普通の HF に切り替わる (`levels.py` の `correlated=True`)。
- 開殻状態は UHF 参照の上で計算する。

## 参考文献

- A. Szabo, N. S. Ostlund, *Modern Quantum Chemistry*, 6 章 (多体摂動論)。H₂ の例を含む。
- C. Møller, M. S. Plesset, *Phys. Rev.* **46**, 618 (1934)。
- F. Jensen, *Introduction to Computational Chemistry*, 3rd ed., 電子相関法の章。
