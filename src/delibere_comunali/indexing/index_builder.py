from pathlib import Path
from typing import Iterable, Tuple
import re
from delibere_comunali.indexing.token_pool import TokenPool, InvertedIndex


def simple_tokenize(text: str):
    return [t for t in re.findall(r"\w+", text.lower()) if t]


def build_index(docs: Iterable[Tuple[int, str]], out_dir: Path):
    tp = TokenPool()
    idx = InvertedIndex(tp)
    for doc_id, text in docs:
        toks = simple_tokenize(text)
        tids = tp.batch_intern(toks)
        idx.add_doc(doc_id, tids)
    idx.freeze()
    idx.save(out_dir)
    return tp, idx