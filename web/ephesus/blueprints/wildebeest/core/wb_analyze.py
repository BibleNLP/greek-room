"""
Script to run Wildebeest Analysis
"""
import flask
import json
import logging
import subprocess
from tempfile import NamedTemporaryFile
from pathlib import Path


# TODO: Improve import invocation
wb_analysis = __import__("wildebeest.wb-analysis")


_LOGGER = logging.getLogger(__name__)

# Hardcode args for wildebeest-analysis
args = {"lc": None, "data_directory": None, "max_examples": 5, "max_cases": 100}


def get_wb_analysis(verses: list, ref_id_dict: dict):
    """Run wildebeest-analysis script and return anlaysis as JSON"""

    _LOGGER.info(verses)

    # Convert verses list to string for Wildebeest
    verses = "\n".join(verses)

    # Use CLI for wildebeest for now.
    # TODO: Change this internal API call.
    wb_workspace_dir = flask.current_app.config["WILDEBEEST_UPLOAD_DIR"]
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        errors="surrogateescape",
        delete=False,
        dir=wb_workspace_dir,
    ) as verses_file, NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False, dir=wb_workspace_dir
    ) as ref_id_file, NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        errors="surrogateescape",
        delete=False,
        dir=wb_workspace_dir,
    ) as wb_json_file:
        verses_file.write(verses)
        ref_id_file.write("\n".join(ref_id_dict.values()))

        verses_file_path = Path(wb_workspace_dir) / Path(verses_file.name)

        ref_id_file_path = Path(wb_workspace_dir) / Path(ref_id_file.name)

        wb_json_file_path = Path(wb_workspace_dir) / Path(wb_json_file.name)

    wb_analysis_result = subprocess.run(
        [
            "python",
            "-m",
            "wildebeest.wb-analysis",
            "-i",
            f"{verses_file_path}",
            "-r",
            f"{ref_id_file_path}",
            "-j",
            f"{wb_json_file_path}",
        ],
    )

    with wb_json_file_path.open(mode="rb") as wb_output_file:
        wb_output = json.load(wb_output_file)

    logging.info(wb_output)

    # Clean-up temporary files
    verses_file_path.unlink(missing_ok=True)
    ref_id_file_path.unlink(missing_ok=True)
    wb_json_file_path.unlink(missing_ok=True)

    return wb_output

    # wb = wb_analysis.WildebeestAnalysis(args)
    # wb.ref_id_dict = ref_id_dict
    # wb.collect_counts_and_examples(verses, progress_bar=False)
    # wb.aggregate()  # Aggregate raw counts and examples into analysis.
    # wb.remove_empty_dicts()

    # return json.dumps(wb.analysis)
