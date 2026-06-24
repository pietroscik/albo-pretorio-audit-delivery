from array import array
from pathlib import Path
from typing import Iterable, List, Dict, Optional, Tuple


class TokenPool:
    """Intern string tokens to integer ids (0..N-1)."""
    def __init__(self) -> None:
        self._token_to_id: Dict[str, int] = {}
        self._id_to_token: List[str] = []

    def intern(self, token: str) -> int:
        tid = self._token_to_id.get(token)
        if tid is None:
            tid = len(self._id_to_token)
            self._token_to_id[token] = tid
            self._id_to_token.append(token)
        return tid

    def batch_intern(self, tokens: Iterable[str]) -> List[int]:
        return [self.intern(t) for t in tokens]

    def token(self, tid: int) -> str:
        return self._id_to_token[tid]

    def n_tokens(self) -> int:
        return len(self._id_to_token)

    def save_vocab(self, path: Path) -> None:
        path.write_text("\n".join(self._id_to_token), encoding="utf-8")

    def load_vocab(self, path: Path) -> None:
        toks = path.read_text(encoding="utf-8").splitlines()
        self._id_to_token = toks
        self._token_to_id = {t: i for i, t in enumerate(toks)}


class InvertedIndex:
    """
    Builder for an inverted index storing postings as compact arrays.
    Build phase: use add_doc(doc_id, token_ids).
    Freeze phase: pack all postings into a flat array('I') and offsets array('I').
    """
    def __init__(self, token_pool: TokenPool) -> None:
        self.tp = token_pool
        # temporary mutable posting lists (token_id -> array of doc_ids)
        self._build_postings: Dict[int, array] = {}
        # used to avoid duplicate doc_id writes per token (store last appended)
        self._last_doc_for_token: Dict[int, int] = {}

        # frozen structures
        self._flat_postings: Optional[array] = None
        self._offsets: Optional[array] = None  # length = n_tokens + 1

    def add_doc(self, doc_id: int, token_ids: Iterable[int]) -> None:
        # expected token_ids may contain duplicates; iterate unique preserving order
        seen = set()
        for tid in token_ids:
            if tid in seen:
                continue
            seen.add(tid)
            arr = self._build_postings.get(tid)
            if arr is None:
                arr = array("I")
                self._build_postings[tid] = arr
            # avoid duplicate doc_id entries
            last = self._last_doc_for_token.get(tid)
            if last == doc_id:
                continue
            arr.append(doc_id)
            self._last_doc_for_token[tid] = doc_id

    def freeze(self) -> None:
        n = self.tp.n_tokens()
        flat = array("I")
        offsets = array("I", [0])  # offsets[0] = 0
        for tid in range(n):
            posting = self._build_postings.get(tid)
            if posting is None:
                # empty posting -> offset doesn't change
                offsets.append(offsets[-1])
                continue
            # extend flat array
            flat.extend(posting)
            offsets.append(len(flat))
        self._flat_postings = flat
        self._offsets = offsets
        # free build-time structures
        self._build_postings = {}
        self._last_doc_for_token = {}

    def postings_for_token_id(self, tid: int) -> memoryview:
        if self._flat_postings is None or self._offsets is None:
            raise RuntimeError("Index not frozen")
        start = self._offsets[tid]
        end = self._offsets[tid + 1]
        # expose as memoryview of underlying buffer (no new allocations of ints)
        raw = self._flat_postings
        mv = memoryview(raw)  # memoryview over array('I')
        # return view sliced to required region (still zero-copy)
        return mv[start:end]

    def postings_for_token(self, token: str) -> memoryview:
        tid = self.tp._token_to_id.get(token)
        if tid is None:
            # return empty memoryview
            return memoryview(array("I"))
        return self.postings_for_token_id(tid)

    def save(self, dirpath: Path) -> None:
        dirpath.mkdir(parents=True, exist_ok=True)
        # save flat postings as raw bytes and offsets as 32-bit ints
        (dirpath / "vocab.txt").write_text("\n".join(self.tp._id_to_token), encoding="utf-8")
        with (dirpath / "postings.bin").open("wb") as f:
            f.write(self._flat_postings.tobytes())
        with (dirpath / "offsets.bin").open("wb") as f:
            f.write(self._offsets.tobytes())

    def load(self, dirpath: Path) -> None:
        self.tp.load_vocab(dirpath / "vocab.txt")
        with (dirpath / "postings.bin").open("rb") as f:
            b = f.read()
            self._flat_postings = array("I")
            self._flat_postings.frombytes(b)
        with (dirpath / "offsets.bin").open("rb") as f:
            b = f.read()
            self._offsets = array("I")
            self._offsets.frombytes(b)