import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union

from jiwer import wer
from Levenshtein import distance
from tqdm.auto import tqdm
from whisper.normalizers import EnglishTextNormalizer


@dataclass
class EvaluationResult:
    """
    Result object of the model evaluation
    """

    accuracy = float
    total_test_samples = int

    def __init__(self, accuracy, total_test_samples):
        self.accuracy = accuracy
        self.total_test_samples = total_test_samples

    def __repr__(self):
        return (
            "EvaluationResult("
            + json.dumps(
                {
                    "accuracy": self.accuracy,
                    "total_test_samples": self.total_test_samples,
                }
            )
            + ")"
        )


@dataclass
class EvaluationTestSample:
    """
    Represents one test sample
    """

    reference_text = str
    predicted_text = str

    def __init__(self, reference_text, predicted_text):
        self.reference_text = reference_text
        self.predicted_text = predicted_text

    def update(self, reference_text, predicted_text):
        self.reference_text = reference_text
        self.predicted_text = predicted_text


class TestDatasetLoader:
    """
    Test samples loader
    """

    parent_dir = None
    total_samples = 0

    def __init__(self, parent_dir: Union[Path | str]):
        if isinstance(parent_dir, str):
            self.parent_dir = Path(parent_dir)
        else:
            self.parent_dir = parent_dir

    def _load_test_data(self) -> tuple[str, str]:
        """
        Loader function to validate inout files and generate samples
        """
        PREDICTED_TEST_SAMPLES_DIR = self.parent_dir / "predicted_texts"
        REFERENCE_TEST_SAMPLES_DIR = self.parent_dir / "reference_texts"

        for filename in os.listdir(PREDICTED_TEST_SAMPLES_DIR.as_posix()):
            match = re.search(r"(\d+)\.txt$", filename)
            if match:
                sample_id = match.group(1)
                pred_file_path = (PREDICTED_TEST_SAMPLES_DIR / filename).as_posix()
                ref_file_name = "ref_sample_" + str(sample_id) + ".txt"
                ref_file_path = (REFERENCE_TEST_SAMPLES_DIR / ref_file_name).as_posix()
                if os.path.exists(ref_file_path):
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
            yield EvaluationTestSample(ref_text, pred_text)


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

    normalizer = None
    accuracy = None
    test_dataset_loader = None
    test_directory = None
    evaluation_config = {}

    def __init__(self, **kwargs):
        self.evaluation_config = {k: v for k, v in kwargs.items() if v is not None}
        if "normalizer" not in self.evaluation_config:
            self.normalizer = EnglishTextNormalizer()
        self.evaluation_config["normalizer"] = str(type(self.normalizer))
        if "parent_dir" not in self.evaluation_config:
            self.test_directory = Path(__file__).parent
        self.test_dataset_loader = TestDatasetLoader(self.test_directory)
        self.evaluation_config["test_directory"] = str(self.test_directory)

    def __repr__(self):
        return "ModelEvaluator(" + json.dumps(self.describe(), indent=4) + ")"

    def describe(self) -> dict:
        """
        Returns the parameters defining the evaluator
        """
        return self.evaluation_config

    def _normalize(self, sample: EvaluationTestSample) -> None:
        """
        Normalize both reference and predicted text
        """
        sample.update(
            self.normalizer(sample.reference_text),
            self.normalizer(sample.predicted_text),
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
                self.evaluation_config["insertion_penalty"],
                self.evaluation_config["deletion_penalty"],
                self.evaluation_config["substitution_penalty"],
            ),
        )
        wer = levenshtein_distance / len(sample.reference_text)
        return wer

    def _calculate_wers(self) -> None:
        """
        Compute WER
        """
        for sample in tqdm(self.test_dataset_loader, desc="Evaluating", ncols=100):
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
        self.accuracy = (1 - final_weighted_wer) * 100

    def evaluate(self, recalculate: bool = False) -> EvaluationResult:
        """
        Triggers the model evaluation
        """
        if not self.accuracy or recalculate:
            self._calculate_model_accuracy()
        return EvaluationResult(self.accuracy, self.test_dataset_loader.total_samples)


eval_config = {"insertion_penalty": 1, "deletion_penalty": 2, "substitution_penalty": 1}

evaluator = ModelEvaluator(**eval_config)
evaluation = evaluator.evaluate()

print(evaluator)
print(evaluation)
print("Model accuracy : {:.2f} %".format(evaluation.accuracy))
