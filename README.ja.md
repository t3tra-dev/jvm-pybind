[[英語/English](README.md)]

# JVM-PyBind

JNI (Java Native Interface) を通じて Python と Java コードをシームレスに統合する JVM バインディングライブラリです。

## 特徴

- **直接的な JNI 統合**: ctypes を使用した低レベル JNI バインディングで最大限のパフォーマンスを実現
- **動的クラス発見**: リフレクションを使用した Java クラス、メソッド、フィールドの自動発見
- **Python インポートフック**: 標準的な Python の import 構文で Java クラスにアクセス可能
- **型変換**: Python と Java 型の自動変換
- **メモリ安全性**: 適切な JNI 参照管理と安全なシャットダウン手順
- **クロスプラットフォーム**: Windows、macOS (ARM64 を含む)、Linux をサポート
- **設定**: pyproject.toml による柔軟な設定

## クイックスタート

### インストール

```bash
pip install jvm-pybind
```

### 基本的な使用方法

```python
# 標準的なPython構文でJavaクラスをインポート
from java.lang import System

# Javaメソッドを直接呼び出し
System.out.println("Hello from JVM!")

# Javaプロパティにアクセス
print(f"Java Version: {System.getProperty('java.version')}")
print(f"Java Vendor: {System.getProperty('java.vendor')}")
```

## コマンドラインインターフェース

jvm-pybind は開発環境での Java 型スタブ管理のための CLI を提供します。

### インストール

IDE サポートと自動補完を有効にするために型スタブをインストール:

```bash
# 既定の java.lang、java.util、java.io をインストール
python -m jvm --install-stub

# 指定した1パッケージだけを生成してインストール
python -m jvm --install-stub="java.lang"

# カンマ区切りでJDKとカスタムJARのパッケージを指定
python -m jvm --install-stub="java.io,mypkg"
```

### アンインストール

不要になった型スタブを削除:

```bash
# 現在の仮想環境からJava型スタブを削除
python -m jvm --uninstall-stub
```

### PTH ファイルインストール

仮想環境で自動的に JVM インポートを有効にする .pth ファイルをインストール:

```bash
# 自動インポート用の jvm.pth ファイルをインストール
python -m jvm --install-pth
```

これにより、仮想環境の `site-packages` ディレクトリに `jvm.pth` ファイルが作成され、Python 起動時に自動的に JVM モジュールがインポートされ、手動初期化なしでシームレスに Java クラスをインポートできるようになります。

### 機能

**型スタブ管理:**

- **スタブインストール**: カンマ区切りで指定した Java パッケージの型スタブを生成してインストール
- **スタブアンインストール**: インストールされた全ての Java 型スタブをクリーンに削除
- **自動生成**: 必要に応じて JVM インストールから新しいスタブを生成
- **仮想環境検出**: venv、virtualenv、conda、その他の Python 環境マネージャーと連携

**PTH ファイル管理:**

- **PTH ファイルインストール**: Python 起動時に自動的に JVM モジュールをインポートする `jvm.pth` ファイルを仮想環境に作成
- **自動インポート**: 手動の JVM 初期化なしでシームレスな Java クラスインポートを実現
- **仮想環境安全性**: アクティブな仮想環境内でのみ動作し、分離されたセットアップを保証

**既定のパッケージ:**

- `java.lang` - Java コアクラス (String、System、Object 等)
- `java.util` - コレクションとユーティリティ (List、Map、ArrayList 等)
- `java.io` - 入出力クラス (File、InputStream、OutputStream 等)

`[tool.jvm].classpath` に含まれる JAR または class directory のパッケージも、`--install-stub="mypkg"` のように指定できます。

### 要件

- **仮想環境**: CLI 操作にはアクティブな仮想環境が必要
- **JVM インストール**: スタブ生成のために Java がインストールされ、アクセス可能である必要があります

### 例

```bash
# 仮想環境の作成とアクティベート
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# jvm-pybindのインストール
pip install jvm

# IDEサポート用にJDKとカスタムJARの型スタブをインストール
python -m jvm --install-stub="java.lang,mypkg"

# または自動JVMインポート用のPTHファイルをインストール
python -m jvm --install-pth

# IDEで自動補完が利用可能になります
from java.lang import System  # IDEが利用可能なメソッドを表示
```

### ヘルプ

```bash
python -m jvm --help
```

出力:

```
usage: jvm [-h] (--install-stub [PACKAGES] | --uninstall-stub | --install-pth)

JVM-PyBind: Python bindings for JVM with type stub management

options:
  -h, --help         show this help message and exit
  --install-stub [PACKAGES]
                     Install comma-separated Java package stubs; defaults to
                     java.lang,java.util,java.io
  --uninstall-stub   Remove JDK type stubs from the current virtual environment
  --install-pth      Install jvm.pth file to enable automatic JVM import in
                     virtual environment

Examples:
  python -m jvm --install-stub="java.lang"       Install one package stub
  python -m jvm --install-stub="java.io,mypkg"  Install multiple package stubs
  python -m jvm --uninstall-stub   Remove JDK type stubs from virtual environment
  python -m jvm --install-pth      Install jvm.pth file to enable automatic JVM import
```

### カスタム Java クラスの使用

```toml
# pyproject.toml
[tool.jvm]
java-version = "21"
classpath = ["./hello.jar"]
```

相対クラスパスは、この設定を書いた `pyproject.toml` のディレクトリを基準に解決されます。JAR 内のパッケージとクラスは自動的に検出され、通常の Python import と同じ形で利用できます。

```python
import jvm  # Java import hookを有効化
from mypkg import Hello

print(Hello.greet("World"))
```

IDE 用スタブは、同じ設定を読み込めるディレクトリから生成します。

```bash
python -m jvm --install-stub="mypkg"
```

メソッド、フィールド、コンストラクタの署名は、クラスロード後に Java Reflection と JNI から取得されます。オーバーロード、primitive 型、オブジェクト型、配列型を署名に基づいて呼び分けます。

## 設定

`pyproject.toml`ファイルで jvm-pybind を設定します:

```toml
[tool.jvm]
java-version = "17"  # 使用するJavaバージョン
classpath = [        # 含めるJARファイルとディレクトリ
    "path/to/your.jar",
    "path/to/classes/"
]

[tool.jvm.deps]
maven = [            # Maven依存関係 (将来の機能)
    "org.apache.commons:commons-lang3:3.12.0"
]
```

## システム要件

### Java 実行環境

- **Java 17** (推奨、設定可能)
- サポートされる JDK ディストリビューション:
  - Oracle JDK
  - Eclipse Adoptium (旧 AdoptOpenJDK)
  - Amazon Corretto
  - Microsoft Build of OpenJDK
  - Azul Zulu
  - OpenJDK

### Python

- **Python 3.12+**
- サポートされるプラットフォーム:
  - Windows (x64)
  - macOS (Intel および Apple Silicon)
  - Linux (x64、ARM64)

## アーキテクチャ

jvm-pybind は以下の主要コンポーネントで構成されています:

- **JVMLoader**: JVM の初期化と libjvm ライブラリの読み込み
- **JNIHelper**: 型安全性を備えた低レベル JNI 関数バインディング
- **JVM**: Java クラス発見とメソッド実行のメインインターフェース
- **プロキシクラス**: Java パッケージ、クラス、オブジェクトの Python ラッパー
- **インポートフック**: Python のインポートシステムとの統合

## 高度な使用方法

### 直接的な JNI アクセス

```python
import jvm

# JVMインスタンスを取得
jvm_instance = jvm.get_jvm()

# Javaクラスを検索
string_class = jvm_instance.find_class("java.lang.String")

# クラス情報にアクセス
print(f"メソッド数: {len(string_class.methods)}")
print(f"フィールド数: {len(string_class.fields)}")
```

### メモリ管理

ライブラリは自動的に JNI 参照を管理しますが、明示的にメモリを制御することも可能です:

```python
from java.lang import System

# JVMはPython終了時に自動的にシャットダウンされます
# 明示的な制御の場合:
jvm.shutdown()
```

## 内部 API リファレンス

> 📋 **注意**: このセクションは上級ユーザーと開発者向けの内部 API について説明します。ほとんどの用途では、高レベルな import 構文 (`from java.lang import System`) の使用を推奨します。

### JVM インスタンス管理

```python
import jvm

# 現在のJVMインスタンスを取得 (実行中の場合)
jvm_instance = jvm.get_jvm()  # JVMが開始されていない場合はNoneを返す

# カスタム設定でJVMを開始
from jvm.config import Config
from jvm.loader import JVMLoader

config = Config(java_version="17", classpath=["path/to/jar"], deps={})
jvm_instance = JVMLoader(config).start()
```

### 低レベルクラスアクセス

```python
# 名前でJavaクラスを検索
java_class = jvm_instance.find_class("java/lang/String")
print(f"クラス: {java_class.name}")
print(f"メソッド数: {len(java_class.methods)}")
print(f"フィールド数: {len(java_class.fields)}")

# クラスのメソッドとフィールドにアクセス
for method in java_class.methods:
    print(f"メソッド: {method.name}({', '.join(method.parameters)}) -> {method.return_type}")
    print(f"静的: {method.is_static}")
```

### 直接的な JNI 操作

```python
# 基盤となるJNIヘルパーにアクセス
jni = jvm_instance.jni

# クラスを検索してメソッドIDを取得
string_class = jni.FindClass("java/lang/String")
length_method = jni.GetMethodID(string_class, "length", "()I")

# Java文字列を作成
java_str = jni.NewStringUTF("Hello World")

# メソッドを呼び出し
length = jni.CallIntMethod(java_str, length_method)
print(f"文字列の長さ: {length}")
```

### パッケージ発見

```python
# パッケージ内のクラスを発見
classes = jvm_instance.discover_package_classes("java.util")
for class_name in classes:
    print(f"クラスを発見: {class_name}")
```

### プロキシオブジェクト

```python
from jvm.proxy import ClassProxy, PackageProxy

# Javaパッケージのプロキシを作成
java_lang = PackageProxy(jvm_instance, "java.lang")
system_class = java_lang.System  # ClassProxyを返す

# 静的メソッドにアクセス
system_class.gc()  # System.gc()を呼び出し
property_value = system_class.getProperty("java.version")
```

### 設定アクセス

```python
from jvm.config import Config

# pyproject.tomlから設定を読み込み
config = Config.from_pyproject()
print(f"Javaバージョン: {config.java_version}")
print(f"クラスパス: {config.classpath}")
print(f"依存関係: {config.deps}")

# カスタム設定を作成
custom_config = Config(
    java_version="11",
    classpath=["/path/to/custom.jar"],
    deps={"maven": ["org.apache.commons:commons-lang3:3.12.0"]}
)
```

### 型変換

```python
from jvm.typeconv import to_java, to_python

# Python値をJavaに変換
java_string = to_java(jvm_instance, "Hello")
java_int = to_java(jvm_instance, 42)
java_bool = to_java(jvm_instance, True)

# Java値をPythonに変換
python_value = to_python(jvm_instance, java_string)
```

### 例外処理

```python
from jvm.jvm import JNIException

try:
    # 失敗する可能性のあるJNI操作
    unknown_class = jvm_instance.find_class("com/nonexistent/Class")
except JNIException as e:
    print(f"JNIエラー: {e}")
```

### 利用可能なクラスとメソッド

インポートして使用できる主要なクラス:

| クラス          | 目的                        | 使用例                          |
| --------------- | --------------------------- | ------------------------------- |
| `jvm.JVM`       | メイン JVM インターフェース | `jvm_instance.find_class()`     |
| `jvm.JNIHelper` | 低レベル JNI 関数           | `jni.FindClass()`               |
| `jvm.Config`    | 設定管理                    | `Config.from_pyproject()`       |
| `jvm.JVMLoader` | JVM 初期化                  | `JVMLoader(config).start()`     |
| `jvm.proxy.*`   | Java オブジェクトプロキシ   | `ClassProxy()`, `ObjectProxy()` |

## 開発

### 開発環境の設定

```bash
# リポジトリをクローン
git clone https://github.com/t3tra-dev/jvm-pybind.git
cd jvm-pybind

# 環境の初期化
./reinstall.sh  # または手動で仮想環境を作成
```

### テストの実行

```bash
# サンプルを実行
cd examples/hello
python main.py
```

### プロジェクト構造

```
jvm-pybind/
├── src/jvm/           # メインパッケージ
│   ├── __init__.py    # パッケージ初期化
│   ├── jvm.py         # JVMインターフェース
│   ├── jni.py         # JNIバインディング
│   ├── loader.py      # JVMローダー
│   ├── proxy.py       # Javaオブジェクトプロキシ
│   ├── config.py      # 設定管理
│   ├── typeconv.py    # 型変換ユーティリティ
│   └── import_hook/   # Pythonインポートフック
├── examples/          # 使用例
└── tests/             # テストスイート
```

## サポートされる Java 型

### プリミティブ型

- `boolean` ↔ `bool`
- `int` ↔ `int`
- `long` ↔ `int`
- `float` ↔ `float`
- `double` ↔ `float`
- `String` ↔ `str`

### 複合型

- Java オブジェクトはプロキシクラスでラップ
- 配列とコレクション (計画中)
- リフレクションによるカスタムクラス

## パフォーマンス考慮事項

- **JVM 起動**: 最初の Java インポート時に JVM が遅延初期化されます
- **メモリ使用量**: JNI 参照は自動的に管理されます
- **メソッド呼び出し**: 最適なパフォーマンスのための直接 JNI 呼び出し
- **ARM64 最適化**: Apple Silicon 向けの特別な最適化

## トラブルシューティング

### よくある問題

1. **Java が見つからない**: Java がインストールされ、`JAVA_HOME`が設定されていることを確認
2. **ClassNotFoundException**: クラスパス設定を確認
3. **メモリエラー**: アプリケーションに十分なヒープ空間があることを確認

### デバッグモード

デバッグログを有効にする:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from java.lang import System  # デバッグ出力を表示
```

## コントリビューション

コントリビューションを歓迎します！プルリクエストをお気軽に提出してください。

1. リポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを開く

## ライセンス

このプロジェクトは MIT ライセンスの下でライセンスされています - 詳細は[LICENSE](LICENSE)ファイルをご覧ください。

## 謝辞

- JNI 統合に Python の ctypes を使用して構築
- JPype および類似の Java-Python ブリッジプロジェクトからインスピレーション
- Python と Java コミュニティに特別な感謝

## ロードマップ

### 高優先度

- [x] **カスタム Java クラスのインポートサポート** - カスタムクラスに対する`from mypkg import MyClass`構文の実現
- [ ] **強化された型変換** - より多くの Java 型 (配列、コレクション等) のサポート
- [ ] **包括的なテストスイート** - 全機能の完全なテストカバレッジ

### 中優先度

- [ ] **Maven 依存関係解決** - Maven 依存関係の自動ダウンロードと管理
- [ ] **Java コレクションサポート** - Java List、Map 等とのネイティブな Python 統合
- [ ] **パフォーマンス最適化** - メソッド呼び出しの最適化とキャッシュ

### 低優先度

- [ ] **コールバックサポート** - Java コードから Python 関数の呼び出しを可能に
- [ ] **高度なデバッグツール** - より良いエラーメッセージとデバッグ機能
- [x] **IDE 統合** - Java クラスの型ヒントと自動補完

## 技術詳細

### JNI 統合の仕組み

このライブラリは、ctypes を使用して JNI (Java Native Interface) と直接通信します。以下の手順で動作します:

1. **JVM 初期化**: `JNI_CreateJavaVM`を呼び出して JVM を起動
2. **クラス発見**: Java リフレクションを使用してクラス情報を取得
3. **メソッド呼び出し**: JNI 関数を通じて Java メソッドを呼び出し
4. **型変換**: Python と Java 間での自動型変換
5. **メモリ管理**: JNI ローカル・グローバル参照の適切な管理

### 安全性とパフォーマンス

- **メモリリーク防止**: すべての JNI 参照を適切に管理
- **例外処理**: Java の例外を Python の例外に変換
- **スレッドセーフティ**: マルチスレッド環境での安全な動作
- **ARM64 最適化**: Apple Silicon Mac での特別な最適化

### 設定オプション

`pyproject.toml`で以下の設定が可能です:

```toml
[tool.jvm]
# Java バージョン (デフォルト: "17")
java-version = "11"

# クラスパス (JARファイルやディレクトリのリスト)
classpath = [
    "lib/my-library.jar",
    "build/classes/",
    "/absolute/path/to/classes/"
]

# 将来的な機能: Maven依存関係
[tool.jvm.deps]
maven = [
    "org.apache.commons:commons-lang3:3.12.0",
    "com.google.guava:guava:31.1-jre"
]
```
