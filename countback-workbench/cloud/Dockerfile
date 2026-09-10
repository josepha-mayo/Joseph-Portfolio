ARG BASE_IMAGE=public.ecr.aws/lambda/python:3.13
FROM ${BASE_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OPENBLAS_NUM_THREADS=2 \
    OMP_NUM_THREADS=2
COPY requirements.txt /opt/countback/requirements.txt
RUN python -m pip install --no-cache-dir --only-binary=:all: \
    --report /opt/countback/install-report.json \
    -r /opt/countback/requirements.txt && python -m pip check
COPY engine ${LAMBDA_TASK_ROOT}/engine
COPY cloud ${LAMBDA_TASK_ROOT}/cloud
COPY LICENSE ${LAMBDA_TASK_ROOT}/LICENSE
CMD ["cloud.handler.handler"]
