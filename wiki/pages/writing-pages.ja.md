# ページの書き方

## ページを追加する

1. `wiki/pages/<section>/<topic>.md` を作る (小文字、ハイフン区切り: `potential-energy-surface.md`)。
2. `wiki/mkdocs.yml` の `nav` の、そのセクションの下に追加する。
3. セクションの `index.md` からリンクする。

## 翻訳

どのページにも、隣に日本語訳がある: `page.md` (英語) と `page.ja.md` (日本語)。`mkdocs.yml` の `i18n` プラグインが両方の言語をビルドし、言語切り替えを加える。`.ja.md` のないページは英語版で代用される。

- まず英語のページを書くか変更し、同じコミットでその `.ja.md` も更新する。
- 新しいナビゲーションのタイトルには、`mkdocs.yml` の `nav_translations` に日本語の項目が必要である。
- リンクのアンカーは言語間で同じにする: 他のページからリンクされる日本語の見出しには、英語のアンカーを明示的につける。例: `## 結合の切断 { #bond-breaking }`。
- コード、プログラムの出力、図の中の文字は英語のままにする。
- 日本語の段落はソース上で 1 行にする。Markdown は段落内の改行を空白に変えるので、日本語の文字の間に空白が見えてしまう。折り返して書いてもよいが、そのあとで `python3 wiki/tools/join_ja.py wiki/pages/**/*.ja.md` を実行して行をつなぐ。

## ページのひな形

```markdown
# ポテンシャルエネルギー曲面

!!! info "前提知識"
    [ボルン–オッペンハイマー近似](born-oppenheimer.md)

一段落の要約: それが何であり、ここでなぜ重要か。

## 考え方

平易な言葉での概念、次に式。

## 例

計算例。できればこのプロジェクトの数値を使う。

## [h_clusters](https://github.com/skachano/h_clusters) での登場箇所 { #where-this-appears-in-h_clusters }

- コード: `worker/src/hclust/levels.py`
- 計画: `doc/Plan.md` §2.1
- [ウェブアプリ](app:): その話題を示すビュー。例: [H₃⁺](app:s/3/1/1)

## 参考文献

- Jensen, *Introduction to Computational Chemistry*, §12.1
```

## 記法

**数式**は LaTeX で書く。行内: `$E = h\nu$` は $E = h\nu$ になる。別行立て:

```latex
$$
\hat{H}\Psi = E\Psi
$$
```

$$
\hat{H}\Psi = E\Psi
$$

**注記** (`!!! note`、`!!! warning`、`!!! example`。折りたたむには `???` を使う):

!!! warning "自己相互作用誤差"
    DFT では電子が自分自身と反発してしまう。

**図**は言語名 `mermaid` のコードブロックで書く。

**リンク**は `.md` ファイルへの相対 Markdown リンクで書く。例: `[ハートリー–フォック法](../methods/hartree-fock.md)`。strict ビルドは壊れたリンクを報告する。

**Web アプリへのリンク**は `app:` で始め、そのあとにキャンペーンを除いたアプリのルートを書く: `[H₃⁺](app:s/3/1/1)` は H₃⁺ の化学種ページ (サイズ、電荷、多重度) を、`app:trends` は傾向を、`app:` はグリッドを開く。baseline 以外のキャンペーンには `c/<campaign>/` をつける: `app:c/demo/s/5/1/1`。日本語のページからはアプリが日本語で開く。フック `wiki/hooks/app_links.py` がこれを実際のアドレス (ローカルの開発サーバー、または GitHub Pages 上のアプリ) に変える。アプリにない状態への化学種のルートは strict ビルドを失敗させる。それ以外のルートは検査されないので、プレビューで一度開いて確かめる。

化学種はどこに出てきても、アプリのそのページへリンクする。ページを書いたら次を実行する:

```sh
python3 wiki/tools/link_species.py wiki/pages/**/*.md
```

足りないリンク (基底状態、または式の隣に書かれたスピン状態: 「三重項 H₃⁺」) を加える。いくつものユニットからなる式は、全体として、それらを合わせた化学種へリンクする: H₃⁺·H₂ と (H₂)₂ は H₅⁺ と H₄ を開く。+ で書いた和、たとえばチャネルの生成物も同じで、H₆⁺ → H₅⁺ + H の「H₅⁺ + H」は H₆⁺ を開く。各項がすでに個別にリンクされていてもそうなる。見出し、コード、数式、H⁻(H₂)ₖ のように数が変数の族、そしてアプリにない H 原子と陽子 H⁺ (和の外にあるとき) には触れない。見出し「h_clusters での登場箇所」の h_clusters はリポジトリへリンクし、アプリへリンクした「ウェブアプリ」の項目は、そのページの話題を示すビューを指す。

## プレビューと確認

```sh
docker compose --profile docs up docs        # ライブプレビュー、http://localhost:8001
docker compose run --rm docs build --strict  # 壊れたリンクやナビゲーションの誤りで失敗する
```

ドキュメント用イメージ (`wiki/Dockerfile`) は MkDocs Material に i18n プラグインを加えたものである。バージョンを変えたあとは `docker compose build docs` で作り直す。
