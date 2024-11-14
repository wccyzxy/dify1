from core.pipeline.base_pipeline import BasePipeline
from core.pipeline.entities.pipeline_entities import PipelineExecutionContext, BasePipelineData
from typing import List, Dict, Any
from extensions.ext_database import db
from models.dataset import Dataset, Document, DocumentSegment
from sqlalchemy import func
from core.rag.retrieval.dataset_retrieval import DatasetRetrieval
from core.rag.retrieval.retrieval_methods import RetrievalMethod
from core.app.app_config.entities import DatasetRetrieveConfigEntity


class SimpleRAGPipeline(BasePipeline):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.pipeline_name = "SimpleRAGPipeline"

    def process(self, context: PipelineExecutionContext) -> PipelineExecutionContext:
        relevant_docs = self._fetch_dataset_retriever(context.query.query, self.config)
        print(f"relevant_docs: {relevant_docs}")
        relevant_data = BasePipelineData()
        relevant_data.data = relevant_docs
        relevant_data.data_from = "RAG"
        context.pipeline_datas.append(relevant_data)
        return context
    
    def _fetch_dataset_retriever(self, query: str, rag_config: Dict[str, Any]) -> list[dict[str, Any]]:
        available_datasets = []
        dataset_ids = rag_config.get("dataset_ids", [])

        # Subquery: Count the number of available documents for each dataset
        subquery = (
            db.session.query(Document.dataset_id, func.count(Document.id).label("available_document_count"))
            .filter(
                Document.indexing_status == "completed",
                Document.enabled == True,
                Document.archived == False,
                Document.dataset_id.in_(dataset_ids),
            )
            .group_by(Document.dataset_id)
            .having(func.count(Document.id) > 0)
            .subquery()
        )

        results = (
            db.session.query(Dataset)
            .join(subquery, Dataset.id == subquery.c.dataset_id)
            .filter(Dataset.id.in_(dataset_ids))
            .all()
        )
        print(f"results: {results}")
        for dataset in results:
            # pass if dataset is not available
            if not dataset:
                continue
            available_datasets.append(dataset)
        all_documents = []
        dataset_retrieval = DatasetRetrieval()
        print(f"all_documents: {all_documents}")

        if rag_config.get("retrieval_mode", None) == DatasetRetrieveConfigEntity.RetrieveStrategy.MULTIPLE.value:
            if rag_config.get("multiple_retrieval_config", {}).get("reranking_mode", None) == "reranking_model":
                reranking_model = {
                    "reranking_provider_name": rag_config.get("multiple_retrieval_config", {}).get("reranking_model", {}).get("provider", None),
                    "reranking_model_name": rag_config.get("multiple_retrieval_config", {}).get("reranking_model", {}).get("model", None),
                }
                weights = None
            elif rag_config.get("multiple_retrieval_config", {}).get("reranking_mode", None) == "weighted_score":
                reranking_model = None
                vector_setting = rag_config.get("multiple_retrieval_config", {}).get("weights", {}).get("vector_setting", None)     
                weights = {
                    "vector_setting": {
                        "vector_weight": vector_setting.get("vector_weight", None),
                        "embedding_provider_name": vector_setting.get("embedding_provider_name", None),
                        "embedding_model_name": vector_setting.get("embedding_model_name", None),
                    },
                    "keyword_setting": {
                        "keyword_weight": rag_config.get("multiple_retrieval_config", {}).get("weights", {}).get("keyword_setting", {}).get("keyword_weight", None)
                    },
                }
            else:
                reranking_model = None
                weights = None
            all_documents = dataset_retrieval.multiple_retrieve(
                '',
                self.config['tenant_id'],
                '',
                '',
                available_datasets,
                query,
                rag_config.get("multiple_retrieval_config", {}).get("top_k", None),
                rag_config.get("multiple_retrieval_config", {}).get("score_threshold", None),
                rag_config.get("multiple_retrieval_config", {}).get("reranking_mode", None),
                reranking_model,
                weights,
                rag_config.get("multiple_retrieval_config", {}).get("reranking_enable", None),
            )

        context_list = []
        if all_documents:
            document_score_list = {}
            page_number_list = {}
            for item in all_documents:
                if item.metadata.get("score"):
                    document_score_list[item.metadata["doc_id"]] = item.metadata["score"]

            index_node_ids = [document.metadata["doc_id"] for document in all_documents]
            segments = DocumentSegment.query.filter(
                DocumentSegment.dataset_id.in_(dataset_ids),
                DocumentSegment.completed_at.isnot(None),
                DocumentSegment.status == "completed",
                DocumentSegment.enabled == True,
                DocumentSegment.index_node_id.in_(index_node_ids),
            ).all()
            if segments:
                index_node_id_to_position = {id: position for position, id in enumerate(index_node_ids)}
                sorted_segments = sorted(
                    segments, key=lambda segment: index_node_id_to_position.get(segment.index_node_id, float("inf"))
                )

                for segment in sorted_segments:
                    dataset = Dataset.query.filter_by(id=segment.dataset_id).first()
                    document = Document.query.filter(
                        Document.id == segment.document_id,
                        Document.enabled == True,
                        Document.archived == False,
                    ).first()

                    resource_number = 1
                    if dataset and document:
                        source = {
                            "metadata": {
                                "_source": "knowledge",
                                "position": resource_number,
                                "dataset_id": dataset.id,
                                "dataset_name": dataset.name,
                                "document_id": document.id,
                                "document_name": document.name,
                                "document_data_source_type": document.data_source_type,
                                "segment_id": segment.id,
                                "retriever_from": "workflow",
                                "score": document_score_list.get(segment.index_node_id, None),
                                "segment_hit_count": segment.hit_count,
                                "segment_word_count": segment.word_count,
                                "segment_position": segment.position,
                                "segment_index_node_hash": segment.index_node_hash,
                            },
                            "title": document.name,
                        }
                        if segment.answer:
                            source["content"] = f"question:{segment.get_sign_content()} \nanswer:{segment.answer}"
                        else:
                            source["content"] = segment.get_sign_content()
                        context_list.append(source)
                        resource_number += 1
        return context_list