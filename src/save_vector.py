import chromadb
from openai import OpenAI
from chunk_md import chunk_mds
from dotenv import load_dotenv
import os

# .env ファイルから環境変数をロード
load_dotenv()

# OpenAI クライアント
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Chroma クライアント（ローカル永続化）
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# コレクション作成（存在しなければ新規作成）
collection = chroma_client.get_or_create_collection(
    name="markdown_rag",
)

chunks = chunk_mds()
print(chunks)
# ---- チャンクを1つずつ処理 ----
for i, chunk in enumerate(chunks):
    text = chunk["content"]

    # 1) OpenAI で埋め込み作成
    emb = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    ).data[0].embedding

    # 2) Chroma に追加
    collection.add(
        ids=[f"chunk-{i}"],            # ユニークID
        documents=[text],              # 本文
        embeddings=[emb],              # ベクトル
        metadatas=[{                   # メタデータ
            "file": chunk["file_name"],
            "heading": chunk["heading"]
        }]
    )

