import math
from collections import Counter
from decimal import Decimal, InvalidOperation

from noomin_api.schemas.profile import ColumnProfile, HistogramBin


def profile_columns(columns: list[str], rows: list[dict[str, str | None]]) -> list[ColumnProfile]:
    profiles = []
    for column in columns:
        present = [row.get(column) for row in rows if row.get(column) not in (None, "")]
        values = [str(value) for value in present]
        unique_count = len(set(values))
        numeric_values = []
        numeric = True
        for value in values:
            try:
                parsed = float(Decimal(value))
            except (InvalidOperation, ValueError, OverflowError):
                numeric = False
                break
            if not math.isfinite(parsed):
                numeric = False
                break
            numeric_values.append(parsed)

        bins = []
        minimum = maximum = average = None
        data_type = "number" if numeric and numeric_values else "text"
        if data_type == "number":
            minimum, maximum = min(numeric_values), max(numeric_values)
            average = math.fsum(value / len(numeric_values) for value in numeric_values)
            span = maximum - minimum
            if minimum == maximum or not math.isfinite(span):
                bins = [HistogramBin(start=minimum, end=maximum, count=len(numeric_values))]
            else:
                bin_count = min(8, max(1, int(math.sqrt(len(numeric_values)))))
                width = span / bin_count
                if width == 0:
                    bins = [HistogramBin(start=minimum, end=maximum, count=len(numeric_values))]
                else:
                    counts = [0] * bin_count
                    for value in numeric_values:
                        index = min(int((value - minimum) / width), bin_count - 1)
                        counts[index] += 1
                    bins = [HistogramBin(start=minimum + index * width, end=maximum if index == bin_count - 1 else minimum + (index + 1) * width, count=count) for index, count in enumerate(counts)]
        category_counts = []
        if data_type == "text":
            category_counts = [
                {"value": value, "count": count}
                for value, count in Counter(values).most_common(10)
            ]
        profiles.append(ColumnProfile(name=column, data_type=data_type, non_null_count=len(values), unique_count=unique_count, minimum=minimum, maximum=maximum, average=average, distribution=bins, category_counts=category_counts))
    return profiles
