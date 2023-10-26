"""
Common utilities in service of the Ephesus application
"""

import os
import re
import shutil
import logging
import secrets
import zipfile
import tempfile
import unicodedata
from pathlib import Path
from collections import Counter

from machine.corpora import (
    UsfmFileTextCorpus,
    extract_scripture_corpus,
    ParatextTextCorpus,
)

from ..constants import (
    USFM_FILE_PATTERNS,
    ZIP_FILE_PATTERN,
    BookCodes,
)

from ..exceptions import (
    InputError,
    FormatError,
)

_LOGGER = logging.getLogger(__name__)


# For stuff (legally) taken from Pallets project
"""
Copyright 2007 Pallets

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

1.  Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

2.  Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the distribution.

3.  Neither the name of the copyright holder nor the names of its
    contributors may be used to endorse or promote products derived from
    this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

_filename_ascii_strip_re = re.compile(r"[^A-Za-z0-9_.-]")
_windows_device_files = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(10)),
    *(f"LPT{i}" for i in range(10)),
}


def secure_filename(filename: str) -> str:
    r"""Pass it a filename and it will return a secure version of it.  This
    filename can then safely be stored on a regular file system and passed
    to :func:`os.path.join`.  The filename returned is an ASCII only string
    for maximum portability.

    On windows systems the function also makes sure that the file is not
    named after one of the special device files.

    >>> secure_filename("My cool movie.mov")
    'My_cool_movie.mov'
    >>> secure_filename("../../../etc/passwd")
    'etc_passwd'
    >>> secure_filename('i contain cool \xfcml\xe4uts.txt')
    'i_contain_cool_umlauts.txt'

    The function might return an empty filename.  It's your responsibility
    to ensure that the filename is unique and that you abort or
    generate a random filename if the function returned an empty one.

    :param filename: the filename to secure
    """
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("ascii", "ignore").decode("ascii")

    for sep in os.sep, os.path.altsep:
        if sep:
            filename = filename.replace(sep, " ")
    filename = str(_filename_ascii_strip_re.sub("", "_".join(filename.split()))).strip(
        "._"
    )

    # on nt a couple of special files are present in each folder.  We
    # have to ensure that the target file is not such a filename.  In
    # this case we prepend an underline
    if (
        os.name == "nt"
        and filename
        and filename.split(".")[0].upper() in _windows_device_files
    ):
        filename = f"_{filename}"

    return filename


def has_filetype(dir: Path, pattern: str, min_count: int = 1) -> bool:
    """Return if `dir` has at least `min_count` file(s)
    within it that matches `pattern`"""
    if not dir or not dir.exists() or not pattern or len(pattern.strip()) == 0:
        return False

    return True if len(list(dir.glob(pattern))) >= min_count else False


def get_book_from_usfm(file_fragment: str) -> BookCodes:
    """Cheap hack to sanity check if a file is indeed USFM
    and return the book code from the `\id` tag (required in USFM)"""
    if not file_fragment or len(file_fragment.strip()) < 4:
        return None

    tokens: list[str] = [token.upper() for token in file_fragment.split()]
    if tokens.count("\ID") > 1:
        raise FormatError("Invalid USFM File. Contains multiple `\id` markers.")
    if tokens.count("\ID") == 0:
        raise FormatError("Invalid USFM File. No `\id` marker found.")
    if tokens.index("\ID") == (len(tokens) - 1):
        raise FormatError("Invalid USFM File. No book code found after`\id` marker.")
    book_code = tokens[tokens.index("\ID") + 1]
    if book_code not in BookCodes:
        raise FormatError(
            f"Invalid USFM File. Invalid/unsupported BookCode {book_code} found."
        )

    return BookCodes(book_code)


# TODO: Add support for Scripture Burrito
def parse_files(input_dir, output_dir, resource_id=secrets.token_urlsafe(6)):
    """
    Parse the uploaded file(s) in `input_dir` and save them in `output_dir`.
    Only allow:
    - Multiple USFM files
    - Zipped archive of USFM files
    - All files within a Paratext project (not zipped)
    - Zipped archive of one Paratext project

    *No* combinations of the above are allowed.
    This means that the upload should either
    only have regular files or one zipped archive.
    """
    try:
        # Check if the `input_dir` has neither .zip
        # nor .sfm files. If so, bail.
        if not has_filetype(input_dir, f"**/{ZIP_FILE_PATTERN}") and not any(
            [has_filetype(input_dir, f"**/{pattern}") for pattern in USFM_FILE_PATTERNS]
        ):
            raise InputError(
                f"The input contains neither ZIP nor USFM files. "
                f"Upload either a zipped archive of USFM files (or a Paratext Project) "
                f"or a collection of USFM files only."
            )

        # Check if the `input_dir` contains a mix of
        # .zip and .sfm files. If so, bail.
        if has_filetype(input_dir, f"**/{ZIP_FILE_PATTERN}") and any(
            [has_filetype(input_dir, f"**/{pattern}") for pattern in USFM_FILE_PATTERNS]
        ):
            raise InputError(
                f"The input contains both ZIP and USFM files. "
                f"Use only one of those types at a time."
            )

        # Check if the `input_dir` contains multiple .zip archives.
        # If so, bail.
        if has_filetype(input_dir, f"**/{ZIP_FILE_PATTERN}", min_count=2):
            raise InputError(
                f"The input contains multiple ZIP files. "
                f"Please upload only one ZIP archive at a time."
            )

        with tempfile.TemporaryDirectory() as extract_dir:
            # Handle Zipped project uploads.
            # These can either by Paratext Projects or
            # a simple collection of USFM files
            # (with .sfm or .usfm extensions).
            if zip_archive := next(input_dir.glob(f"**/{ZIP_FILE_PATTERN}"), False):
                with zipfile.ZipFile(zip_archive, "r") as zip_archive_file:
                    zip_archive_file.extractall(extract_dir)

            # Handle multi-select files upload (not zipped).
            # Simple copy over to the `extract_dir`
            else:
                shutil.copytree(input_dir, extract_dir, dirs_exist_ok=True)

            # Sanity check there *any* USFM files
            if not any(
                [
                    has_filetype(Path(extract_dir), pattern)
                    for pattern in USFM_FILE_PATTERNS
                ]
            ):
                raise InputError(
                    f"The ZIP archive does not contain any identifiable USFM files. "
                    f"Please ensure these are present directly within a directory (not sub-directories)."
                )

            # import pdb

            # pdb.set_trace()

            # Sanity check USFM file format.
            books: Counter = Counter()
            for usfm_file in [
                usfm_file_item
                for pattern in USFM_FILE_PATTERNS
                for usfm_file_item in Path(extract_dir).glob(pattern)
            ]:
                lines: list[str] = []
                with usfm_file.open() as usfm_file_handle:
                    for line in usfm_file_handle:
                        if len(lines) > 2:
                            break
                        if len(line.strip()) > 0:
                            lines.append(line)
                try:
                    books[get_book_from_usfm("\n".join(lines))] += 1
                except FormatError as fme:
                    # Don't act on these errors for now
                    _LOGGER.error("Error in file format: %s", fme)

            # Check if no books were found. If so, bail
            if not books:
                raise InputError(
                    f"No valid format or supported book codes found from the uploaded USFM files"
                )

            # Check if there are multiple USFM files for the same book code.
            # If so, bail.
            if len(books) != sum(books.values()):
                raise InputError(
                    f"The input files contains more than one USFM file "
                    f"for the book code(s): "
                    f"{', '.join([book_code.value for book_code, count in books.items() if count > 1])}",
                )

            # Normalize USFM file extensions
            [
                usfm_file.rename(usfm_file.with_suffix(".SFM"))
                for pattern in USFM_FILE_PATTERNS
                for usfm_file in Path(extract_dir).glob(pattern)
            ]

            corpus = None
            # Check if this is a Paratext project and handle accordingly
            # See: https://github.com/sillsdev/machine.py/blob/19188e173ffdd3c22f2c4eaa68c581d72f2c86c5
            # /machine/corpora/paratext_text_corpus.py#L55C12-L55C12
            if settings := next(Path(extract_dir).glob("**/[sS]ettings.xml"), False):
                corpus = ParatextTextCorpus(settings.resolve(strict=True).parent)
            # else assume it is a plain directory with USFM files
            elif usfm_file := [
                usfm_file_item
                for pattern in USFM_FILE_PATTERNS
                for usfm_file_item in Path(extract_dir).glob(pattern)
            ][0]:
                corpus = UsfmFileTextCorpus(
                    usfm_file.resolve(strict=True).parent,
                    file_pattern=f"*{usfm_file.suffix}",
                )

            if not corpus:
                raise InputError(
                    "Unable to find a parent directory with the USFM files directly within it."
                )

            # Create the output_dir, if it does not exist
            output_dir.mkdir(exist_ok=True)

            # Extract into BibleNLP format
            # This returns verse_text, org_versification, corpus_versification.
            # We don't want to map to org for this use-case.
            verses: [str] = []
            vrefs: [str] = []
            for verse, _, vref in extract_scripture_corpus(corpus):
                verses.append(verse)
                vrefs.append(vref)

            # Check if there was nothing extracted. If so, bail.
            if not any(vrefs):
                raise InputError(
                    "Unable to parse and extract any text from the files provided."
                )

            # Write out cleaned file in output_dir
            with (output_dir / f"{resource_id}.txt").open("w") as cleaned_file:
                cleaned_file.write("\n".join(verses))
                # Add a newline to the end since `.join()` omits it
                cleaned_file.write("\n")

            # Write corresponding vref.txt file
            with (output_dir / "vref.txt").open("w") as vref_file:
                vref_file.write(
                    "\n".join([str(vref) if vref else "" for vref in vrefs])
                )
                # Add a newline to the end since `.join()` omits it
                vref_file.write("\n")

    except InputError as ine:
        _LOGGER.error("Error while parsing and saving the data: %s", ine)
        raise ine
    except Exception as exc:
        _LOGGER.error("Error while parsing and saving the data: %s", exc)
        raise InputError(f"Error while processsing the data.") from exc
