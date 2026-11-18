# ABOUTME: Builds the gateway-only website technology service on port 8009.
# ABOUTME: Downloads pinned GPL fingerprints without adding them to the MIT tree.
FROM python:3.12-slim

WORKDIR /app
COPY shared/ /app/shared/
COPY tech_stack/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY tech_stack/ /app/tech_stack/
ARG RULES_COMMIT=9e52f10a9533c8f7f8d0703c843f7295d56c95a3
RUN python tech_stack/download_rules.py "$RULES_COMMIT" /app/tech_stack/rules \
    && python -c "from tech_stack.rules import RuleSet; RuleSet.load('/app/tech_stack/rules')"

EXPOSE 8009
CMD ["uvicorn", "tech_stack.main:app", "--host", "0.0.0.0", "--port", "8009"]
