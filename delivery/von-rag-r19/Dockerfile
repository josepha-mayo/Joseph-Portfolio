# R16 is the verified, immutable OCR image with the mandated ROCm base ancestry.
# This RAG image still requires an actual build and AMD GPU acceptance run.
FROM awditngm5lljr3aovgqv4xlt240kruwv.lambda-url.us-east-1.on.aws/von-read@sha256:af3000d3d290c4168e5f3d1cfa2df9d95019e4fa680c497546fb62410de7eaad
WORKDIR /app
RUN python3 -m pip install --no-cache-dir --no-deps PyMuPDF==1.26.7 \
 && python3 -c "import torch; assert torch.version.hip and '+rocm' in torch.__version__"
COPY von_rag /app/von_rag
COPY app.py /app/app.py
RUN mkdir -p /run/von-rag /app/index /app/output /app/audit \
 && chmod 700 /run/von-rag
ENV PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
HEALTHCHECK --interval=2s --timeout=2s --start-period=580s --retries=1 \
 CMD ["python3","-m","von_rag.runtime","health"]
ENTRYPOINT ["python3","-m","von_rag.runtime","serve"]
