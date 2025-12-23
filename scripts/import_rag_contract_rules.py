import uuid
from typing import List

import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sentence_transformers import SentenceTransformer


# ============================================
# 設定値（環境に合わせて調整）
# ============================================

QDRANT_URL = "http://localhost:6333"
QDRANT_API_KEY = None  # ローカルなら通常不要。クラウドの場合はキーを設定
COLLECTION_NAME = "rag_contract_rules_mvp"

CSV_PATH = "../data/rag_contract_rules_mvp.csv"

# 埋め込みモデル（例：384次元）
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


# ============================================
# 埋め込み生成クラス
# ============================================

class Embedder:
    def __init__(self, model_name: str):
        # 初回実行時にモデルをダウンロード
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: List[str]) -> List[List[float]]:
        vecs = self.model.encode(texts)
        return vecs.tolist() if hasattr(vecs, "tolist") else vecs


# ============================================
# Qdrantセットアップ
# ============================================

def create_or_recreate_collection(client: QdrantClient, vector_size: int):
    """
    コレクションを作り直す（既にあれば削除してから再作成）。
    MVP なので「毎回まっさら」でOKという前提。
    """
    exists = client.get_collections()
    if any(c.name == COLLECTION_NAME for c in exists.collections):
        print(f"[INFO] コレクション {COLLECTION_NAME} が既に存在するため削除します...")
        client.delete_collection(COLLECTION_NAME)

    print(f"[INFO] コレクション {COLLECTION_NAME} を作成します...")
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=qmodels.VectorParams(
            size=vector_size,
            distance=qmodels.Distance.COSINE,
        ),
    )
    print("[INFO] コレクション作成完了。")


# ============================================
# CSV → Qdrant 取り込み処理
# ============================================

def import_csv_to_qdrant():
    # --- Qdrant クライアント ---
    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
    )

    # --- 埋め込みモデル ---
    embedder = Embedder(EMBEDDING_MODEL_NAME)

    # vector size はモデルから取得（SentenceTransformerの場合）
    test_vec = embedder.encode(["test"])[0]
    vector_size = len(test_vec)
    print(f"[INFO] ベクトル次元: {vector_size}")

    # コレクション作成（既存があれば作り直し）
    create_or_recreate_collection(client, vector_size)

    # --- CSV 読み込み ---
    print(f"[INFO] CSV 読み込み中: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)

    # 必須カラムの確認
    required_cols = ["know_id", "client_company_id", "course_id", "category", "title", "text", "tags"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"CSVに必須カラム {col} が存在しません。")

    # --- ベクトル化するテキストを準備 ---
    # 今回は text をベースに埋め込みを作成（titleやtagsを足したい場合はここで結合）
    texts = df["text"].astype(str).tolist()
    print(f"[INFO] レコード数: {len(texts)}")

    vectors = embedder.encode(texts)

    # --- Qdrant にアップロード ---
    points = []
    for i, row in df.iterrows():
        payload = {
            "know_id": row["know_id"],
            "client_company_id": row["client_company_id"],
            "course_id": row["course_id"],
            "category": row["category"],
            "title": row["title"],
            "text": row["text"],
            "tags": row["tags"],
        }

        point = qmodels.PointStruct(
		id=str(uuid.uuid4()),
            vector=vectors[i],
            payload=payload,
        )
        points.append(point)

    print(f"[INFO] Qdrant に {len(points)} 件のポイントをアップロードします...")
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
        wait=True,
    )
    print("[INFO] アップロード完了！")


if __name__ == "__main__":
    import_csv_to_qdrant()
