import chromadb
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# すでに作成した Chroma DB を読み込む
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_collection("markdown_rag")



def generate_answer(question: str):
    # ---------- 2) 質問を埋め込み ----------
    q_emb = client.embeddings.create(
        model="text-embedding-3-small",
        input=question
    ).data[0].embedding

    # ---------- 3) Chroma で検索 ----------
    results = collection.query(
        query_embeddings=[q_emb],
        n_results=3,                    # 取得するチャンク数
    )

    retrieved_docs = results["documents"][0]
    retrieved_meta = results["metadatas"][0]

    # ---------- 4) コンテキストを作成 ----------
    context = ""
    for doc, meta in zip(retrieved_docs, retrieved_meta):
        context += f"\n[FILE: {meta.get('file')}] [SECTION: {meta.get('heading_path')}]\n{doc}\n"

    # ---------- 5) OpenAI に回答生成 ----------
    prompt = f"""
    あなたは与えられたコンテキスト（経験）に基づいて質問に回答する就活生です。

    # 制約
    - 以下の「コンテキスト」に含まれる情報のみを根拠として回答する
    - コンテキストに答えがない場合は「わかりません」と答える
    - 想像や推測で補完しない

    # コンテキスト
    {context}

    # 質問
    {question}

    # 回答:
    """

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    answer = response.choices[0].message.content
    print("回答:")
    print(answer)

if __name__ == "__main__":
    question = input("質問を入力してください．")
    generate_answer(question)