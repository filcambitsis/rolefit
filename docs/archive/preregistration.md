# RoleFit pre-registration

Hypothesis: verified, structured requirement coverage improves nDCG@10 by at least **+0.05 absolute** over the best of BM25, dense and reciprocal-rank-fusion retrieval under leave-one-persona-out cross validation.

Primary metric: nDCG@10. Secondary: Precision@5, Recall@50 and Recall@25, with eligible candidate counts and judged counts. Report every persona delta, feature-group ablations and a training-size learning curve. Eight independently authored personas, 250–350 human-graded pairs (0–3), one frozen corpus of at least 200 relevant English open jobs. Grade >=2 is relevant for binary metrics. Unjudged items are not automatically negative: report pool coverage and require top-10 judgments before a headline result. Recall on a partial pool is explicitly recall of judged relevant items.

Use regularized logistic regression, fixed C=1 and class weights balanced. Fit scaling on training personas only. Fixed random seed 42. Success is measured against the strongest baseline mean on identical folds. Do not select hyperparameters on the held-out personas. If all methods exceed 0.9, expand with confusable jobs before drawing conclusions.

No experiment has been run at registration. Synthetic demonstration data does not establish the hypothesis. Release the result whether positive or negative.
