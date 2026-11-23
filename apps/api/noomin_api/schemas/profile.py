from pydantic import BaseModel, Field


class HistogramBin(BaseModel):
    start: float
    end: float
    count: int


class CategoryFrequency(BaseModel):
    value: str
    count: int


class ColumnProfile(BaseModel):
    name: str
    data_type: str
    non_null_count: int
    unique_count: int
    minimum: float | None = None
    maximum: float | None = None
    average: float | None = None
    distribution: list[HistogramBin] = Field(default_factory=list)
    category_counts: list[CategoryFrequency] = Field(default_factory=list)


class DatasetProfile(BaseModel):
    dataset_id: str
    row_count: int
    columns: list[ColumnProfile]
