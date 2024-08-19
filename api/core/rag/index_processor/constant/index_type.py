from enum import Enum


class IndexType(Enum):
    PARAGRAPH_INDEX = "text_model"
    QA_MODEL_INDEX = "qa_model"
    QA_INDEX = "qa_index"
    PARENT_CHILD_INDEX = "parent_child_index"
    SUMMARY_INDEX = "summary_index"
