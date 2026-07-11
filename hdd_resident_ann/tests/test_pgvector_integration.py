import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "qso"))
sys.path.insert(0, str(ROOT / "rdo"))

from pgvector_artifact import write_pgvector_layout
from pgvector_adapter import materialize_pgvector_schedule, table_family
from static_layout_main import read_fvecs
from sift1m_pgvector import build_window_plan, split_query_windows


class PgvectorQsoArtifactTest(unittest.TestCase):
    def test_writes_loader_compatible_csv_and_manifest(self):
        vectors = np.asarray([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
        ids = np.asarray([7, 3], dtype=np.int64)

        with tempfile.TemporaryDirectory() as directory:
            artifact = write_pgvector_layout(
                vectors=vectors,
                ids=ids,
                layout_name="window-0-qvlof",
                output_dir=directory,
                source="qso",
            )

            csv_path = Path(artifact["csv_path"])
            manifest_path = Path(artifact["manifest_path"])
            frame = pd.read_csv(csv_path)
            manifest = json.loads(manifest_path.read_text())

            self.assertEqual(csv_path.name, "window_0_qvlof.csv")
            self.assertEqual(frame.columns.tolist(), ["id", "v0", "v1"])
            self.assertEqual(frame["id"].tolist(), [7, 3])
            self.assertEqual(manifest["table_family"]["base"], "window_0_qvlof")
            self.assertEqual(manifest["table_family"]["ivfflat"], "window_0_qvlof_ivfflat")
            self.assertEqual(manifest["table_family"]["hnsw"], "window_0_qvlof_hnsw")


class PgvectorRdoAdapterTest(unittest.TestCase):
    def test_maps_layout_paths_to_pgvector_tables(self):
        self.assertEqual(
            table_family("results/window-2-qvlof.csv"),
            {
                "base": "window_2_qvlof",
                "ivfflat": "window_2_qvlof_ivfflat",
                "hnsw": "window_2_qvlof_hnsw",
            },
        )

        schedule = {
            "move": [(0, "results/window-0-qvlof.csv"), (4, "window-1-qvlof")]
        }
        mapped = materialize_pgvector_schedule(schedule, index_type="hnsw")

        self.assertEqual(
            mapped,
            [
                {"window": 0, "layout": "window_0_qvlof", "table": "window_0_qvlof_hnsw"},
                {"window": 4, "layout": "window_1_qvlof", "table": "window_1_qvlof_hnsw"},
            ],
        )


class Sift1mEntrypointTest(unittest.TestCase):
    def test_reads_fvecs_and_builds_window_table_plan(self):
        vectors = np.asarray([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], dtype=np.float32)

        with tempfile.TemporaryDirectory() as directory:
            vector_path = Path(directory) / "query.fvecs"
            with vector_path.open("wb") as output:
                for vector in vectors:
                    np.asarray([len(vector)], dtype=np.int32).tofile(output)
                    vector.astype(np.float32).tofile(output)

            loaded = read_fvecs(vector_path)

        self.assertTrue(np.array_equal(loaded, vectors))
        windows = split_query_windows(loaded, window_size=2)
        plan = build_window_plan(windows, layout_prefix="sift1m_qvlof", index_type="ivfflat")

        self.assertEqual([window["query_count"] for window in windows], [2, 1])
        self.assertEqual(
            plan["switches"],
            [
                {"window": 0, "layout": "sift1m_qvlof_window_0", "table": "sift1m_qvlof_window_0_ivfflat"},
                {"window": 1, "layout": "sift1m_qvlof_window_1", "table": "sift1m_qvlof_window_1_ivfflat"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
