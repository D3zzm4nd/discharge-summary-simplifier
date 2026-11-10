from .config import settings as s
from .modules.parser import PDFDocumentParser
from .modules.scrubber import PrivacyScrubber
from .modules.splitter import RecursiveTextSplitter
from .modules.embedder import BiomedicalEmbedder
from .modules.vectorstore import ChromaVectorStoreManager
from .modules.retriever import MedlinePlusRetriever
from .modules.prompt import GroundedPromptEngine
from .modules.groundedness import GroundednessEvaluator
from .modules.readability import ReadabilityEvaluator
from .modules.highlight import CriticalInstructionDetector
from .modules.pipeline import DocumentSimplificationPipeline

parser = PDFDocumentParser(s.MAX_FILE_MB, s.MAX_PAGES)
embedder = BiomedicalEmbedder(s.EMBED_MODEL)
vsm = ChromaVectorStoreManager(s.CHROMA_PATH, embedder, s.META_PATH)
retriever = MedlinePlusRetriever(vsm, s.TOP_K, s.MAX_DIST)
engine = GroundedPromptEngine(s.OLLAMA_URL, s.LLM_MODEL)
pipeline = DocumentSimplificationPipeline(PrivacyScrubber(), RecursiveTextSplitter(), vsm, retriever, engine,
    GroundednessEvaluator(embedder, s.GROUND_THRESHOLD), ReadabilityEvaluator(), CriticalInstructionDetector(),
    embedder, s.WORKERS, s.TARGET_SECONDS, s.RETRIEVAL_BUDGET_MS)
