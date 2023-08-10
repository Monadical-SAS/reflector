import re
from pathlib import Path
from typing import Any, List

from jiwer import wer
from Levenshtein import distance
from pydantic import BaseModel, Field, field_validator
from tqdm.auto import tqdm
from whisper.normalizers import EnglishTextNormalizer


class EvaluationResult(BaseModel):
    """
    Result object of the model evaluation
    """
    accuracy: float = Field(default=0.0)
    total_test_samples: int = Field(default=0)


class EvaluationTestSample(BaseModel):
    """
    Represents one test sample
    """

    reference_text: str
    predicted_text: str

    def update(self, reference_text:str, predicted_text:str) -> None:
        self.reference_text = reference_text
        self.predicted_text = predicted_text


class TestDatasetLoader(BaseModel):
    """
    Test samples loader
    """

    test_dir: Path = Field(default=Path(__file__).parent)
    total_samples: int = Field(default=0)

    @field_validator("test_dir")
    def validate_file_path(cls, path):
        """
        Check the file path
        """
        if not path.exists():
            raise ValueError("Path does not exist")
        return path

    def _load_test_data(self) -> tuple[Path, Path]:
        """
        Loader function to validate inout files and generate samples
        """
        PREDICTED_TEST_SAMPLES_DIR = self.test_dir / "predicted_texts"
        REFERENCE_TEST_SAMPLES_DIR = self.test_dir / "reference_texts"

        for filename in PREDICTED_TEST_SAMPLES_DIR.iterdir():
            match = re.search(r"(\d+)\.txt$", filename.as_posix())
            if match:
                sample_id = match.group(1)
                pred_file_path = PREDICTED_TEST_SAMPLES_DIR / filename
                ref_file_name = "ref_sample_" + str(sample_id) + ".txt"
                ref_file_path = REFERENCE_TEST_SAMPLES_DIR / ref_file_name
                if ref_file_path.exists():
                    self.total_samples += 1
                    yield ref_file_path, pred_file_path

    def __iter__(self) -> EvaluationTestSample:
        """
        Iter method for the test loader
        """
        for pred_file_path, ref_file_path in self._load_test_data():
            with open(pred_file_path, "r", encoding="utf-8") as file:
                pred_text = file.read()
            with open(ref_file_path, "r", encoding="utf-8") as file:
                ref_text = file.read()
            yield EvaluationTestSample(reference_text=ref_text, predicted_text=pred_text)


class EvaluationConfig(BaseModel):
    """
    Model for evaluation parameters
    """
    insertion_penalty: int = Field(default=1)
    substitution_penalty: int = Field(default=1)
    deletion_penalty: int = Field(default=1)
    normalizer: Any = Field(default=EnglishTextNormalizer())
    test_directory: str = Field(default=str(Path(__file__).parent))


class ModelEvaluator:
    """
    Class that comprises all model evaluation related processes and methods
    """

    # The 2 popular methods of WER differ slightly. More dimensions of accuracy
    # will be added. For now, the average of these 2 will serve as the metric.
    WEIGHTED_WER_LEVENSHTEIN = 0.0
    WER_LEVENSHTEIN = []
    WEIGHTED_WER_JIWER = 0.0
    WER_JIWER = []

    evaluation_result = EvaluationResult()
    test_dataset_loader = None
    evaluation_config = None

    def __init__(self, **kwargs):
        self.evaluation_config = EvaluationConfig(**kwargs)
        self.test_dataset_loader = TestDatasetLoader(test_dir=self.evaluation_config.test_directory)

    def __repr__(self):
        return f"ModelEvaluator({self.evaluation_config})"

    def describe(self) -> dict:
        """
        Returns the parameters defining the evaluator
        """
        return self.evaluation_config.model_dump()
    def _normalize(self, sample: EvaluationTestSample) -> None:
        """
        Normalize both reference and predicted text
        """
        sample.update(
            self.evaluation_config.normalizer(sample.reference_text),
            self.evaluation_config.normalizer(sample.predicted_text),
        )

    def _calculate_wer(self, sample: EvaluationTestSample) -> float:
        """
        Based on weights for (insert, delete, substitute), calculate
        the Word Error Rate
        """
        levenshtein_distance = distance(
            s1=sample.reference_text,
            s2=sample.predicted_text,
            weights=(
                self.evaluation_config.insertion_penalty,
                self.evaluation_config.deletion_penalty,
                self.evaluation_config.substitution_penalty,
            ),
        )
        wer = levenshtein_distance / len(sample.reference_text)
        return wer

    def _calculate_wers(self) -> None:
        """
        Compute WER
        """
        for sample in tqdm(self.test_dataset_loader, desc="Evaluating"):
            self._normalize(sample)
            wer_item_l = {
                "wer": self._calculate_wer(sample),
                "no_of_words": len(sample.reference_text),
            }
            wer_item_j = {
                "wer": wer(sample.reference_text, sample.predicted_text),
                "no_of_words": len(sample.reference_text),
            }
            self.WER_LEVENSHTEIN.append(wer_item_l)
            self.WER_JIWER.append(wer_item_j)

    def _calculate_weighted_wer(self, wers: List[float]) -> float:
        """
        Calculate the weighted WER from WER
        """
        total_wer = 0.0
        total_words = 0.0
        for item in wers:
            total_wer += item["no_of_words"] * item["wer"]
            total_words += item["no_of_words"]
        return total_wer / total_words

    def _calculate_model_accuracy(self) -> None:
        """
        Compute model accuracy
        """
        self._calculate_wers()
        weighted_wer_levenshtein = self._calculate_weighted_wer(self.WER_LEVENSHTEIN)
        weighted_wer_jiwer = self._calculate_weighted_wer(self.WER_JIWER)

        final_weighted_wer = (weighted_wer_levenshtein + weighted_wer_jiwer) / 2
        self.evaluation_result.accuracy = (1 - final_weighted_wer) * 100

    def evaluate(self, recalculate: bool = False) -> EvaluationResult:
        """
        Triggers the model evaluation
        """
        if not self.evaluation_result.accuracy or recalculate:
            self._calculate_model_accuracy()
        return EvaluationResult(
                accuracy=self.evaluation_result.accuracy,
                total_test_samples=self.test_dataset_loader.total_samples
        )


eval_config = {"insertion_penalty": 1, "deletion_penalty": 2, "substitution_penalty": 1}

evaluator = ModelEvaluator(**eval_config)
evaluation = evaluator.evaluate()

print(evaluator)
print(evaluation)
print("Model accuracy : {:.2f} %".format(evaluation.accuracy))
