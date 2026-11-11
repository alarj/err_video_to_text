function outputs = test_all_models_inimsekkumine_octave (training_file, test_file, cohort, selected_models)
  % Binaarne 0/1 katse: 1 = inimsekkumine vajalik, 0 = ei ole vajalik.
  % Näide:
  % octave11 --eval "addpath('docs/kursusetoo/scripts'); test_all_models_inimsekkumine_octave('log/training_data_b_inimsekkumine.csv','log/test1_data_b_inimsekkumine.csv','b1')"

  pkg load statistics;
  if (nargin < 1), training_file = "log/training_data_b_inimsekkumine.csv"; endif
  if (nargin < 2), test_file = "log/test1_data_b_inimsekkumine.csv"; endif
  if (nargin < 3), cohort = "b1"; endif
  if (nargin < 4), selected_models = {}; endif

  train = readtable (training_file);
  test = readtable (test_file);
  predictors = {"duration_s", "words", "show_speaker_count", "candidate_type", ...
                "internal_speaker_change_count", "distinct_speaker_count", ...
                "dominant_speaker_coverage", "nearest_change_edge_ratio"};
  response = "human_interaction_required";
  validate_binary_data (train, test, predictors, response, cohort);
  svm_tolerance = 1e-3;
  test_rows = size (test, 1);

  [full_x, test_x, groups, encoding] = encode_knn_binary (train, test, predictors);
  all_models = {"Fine Tree", "Medium Tree", "Coarse Tree", "Kernel Naive Bayes", ...
                "Linear SVM", "Quadratic SVM", "Cubic SVM", "Fine Gaussian SVM", ...
                "Medium Gaussian SVM", "Coarse Gaussian SVM", "SVM Kernel", ...
                "Logistic Regression Kernel", "Boosted Trees", "Bagged Trees", "RUSBoosted Trees"};
  if (isempty (selected_models))
    models = all_models; include_knn = true;
  else
    assert (iscell (selected_models) && all (ismember (selected_models, all_models)), ...
            "selected_models peab sisaldama ainult toetatud mitte-kNN mudelinimesid.");
    models = selected_models; include_knn = false;
  endif
  removed_sets = cell (1, 11);
  removed_sets{1} = [];
  for removal_index = 1:8, removed_sets{removal_index + 1} = removal_index; endfor
  removed_sets{10} = [5 6]; removed_sets{11} = 5:8;
  variants = [{"full"}, predictors, {"both_speaker_counts"}, {"all_four_new_features"}];
  plan = build_plan_binary (models, variants, include_knn);
  if (include_knn)
    assert (size (plan, 1) == 498, "Täielik katseplaan peab sisaldama 498 varianti.");
  else
    assert (size (plan, 1) == numel (models) * 9, "Valitud mudelite katseplaan on vigane.");
  endif

  [~, run_name] = fileparts (tempname ());
  output_folder = fullfile (pwd (), "log", [run_name, "_", cohort, "_inimsekkumine_octave"]);
  [ok, msg] = mkdir (output_folder);
  assert (ok, "Tulemuste kausta loomine ebaõnnestus: %s", msg);
  files = initialise_binary_outputs (output_folder, cohort);
  settings_file = fullfile (output_folder, ["settings_", cohort, "_inimsekkumine_octave.mat"]);
  octave_version = version ();
  save (settings_file, "training_file", "test_file", "cohort", "predictors", "response", "models", ...
        "selected_models", "include_knn", "variants", "removed_sets", "plan", "encoding", ...
        "octave_version", "svm_tolerance");
  fprintf ("Tulemuste kaust: %s\n", output_folder);

  successful = 0; failed = 0;
  for n = 1:size (plan, 1)
    model_name = plan{n, 1}; variant_index = plan{n, 2}; family = plan{n, 3};
    k = plan{n, 4}; distance_weight = plan{n, 5}; seed = plan{n, 6};
    variant = variants{variant_index}; removed = removed_sets{variant_index};
    keep = ! ismember (1:8, removed); selected = predictors(keep);
    fprintf ("[%d/%d] %s / %s\n", n, size (plan, 1), model_name, variant);
    try
      rng (seed, "twister");
      if (strcmp (family, "knn"))
        columns = ! ismember (groups, removed);
        mdl = train_knn_binary (full_x(:, columns), train.(response), k, distance_weight);
        predicted = predict (mdl, test_x(:, columns));
        fitted = predict (mdl, full_x(:, columns));
      else
        train_table = train(:, selected);
        train_table.(response) = train.(response);
        mdl = train_classifier_binary (model_name, train_table, response, svm_tolerance);
        predicted = predict (mdl, test(:, selected));
        fitted = predict (mdl, train(:, selected));
      endif
      predicted = numeric_labels (predicted);
      fitted = numeric_labels (fitted);
      assert (numel (predicted) == size (test, 1), "Mudeli ennustuse ridade arv ei ühti testiga.");
      [overall, metrics, confusion, safety] = score_binary_predictions (test.(response), predicted);
      training_accuracy = mean (fitted == train.(response));
      append_csv_binary (files.models, {model_name, variant, family, training_accuracy, ...
        overall(1), overall(2), overall(3), overall(4), safety(1), safety(2), safety(3), safety(4), test_rows, "OK"});
      for c = 1:2
        append_csv_binary (files.perclass, {model_name, variant, c - 1, ...
          metrics(c,1), metrics(c,2), metrics(c,3), metrics(c,4), metrics(c,5), ...
          metrics(c,6), metrics(c,7), metrics(c,8), metrics(c,9), metrics(c,10), metrics(c,11)});
        for d = 1:2
          append_csv_binary (files.confusion, {model_name, variant, c - 1, d - 1, confusion(c, d)});
        endfor
      endfor
      for i = 1:size (test, 1)
        append_csv_binary (files.predictions, {model_name, variant, test.process(i), test.candidate(i), test.(response)(i), predicted(i)});
      endfor
      successful += 1;
    catch err
      append_csv_binary (files.errors, {model_name, variant, err.message});
      append_csv_binary (files.models, {model_name, variant, family, NaN, NaN, NaN, NaN, NaN, NaN, NaN, NaN, NaN, test_rows, "FAILED"});
      fprintf (2, "FAILED: %s / %s: %s\n", model_name, variant, err.message);
      failed += 1;
    end_try_catch
  endfor
  outputs = struct ("OutputFolder", output_folder, "Successful", successful, "Failed", failed, ...
    "Models", files.models, "PerClass", files.perclass, "Confusion", files.confusion, ...
    "Predictions", files.predictions, "Errors", files.errors);
  save (fullfile (output_folder, ["results_", cohort, "_inimsekkumine_octave.mat"]), "outputs");
  fprintf ("Valmis. Õnnestus %d/%d; vigu %d.\n", successful, size (plan, 1), failed);
endfunction

function plan = build_plan_binary (models, variants, include_knn)
  plan = cell (0, 6);
  for m = 1:numel (models)
    for v = 1:9, plan(end + 1, :) = {models{m}, v, "other", NaN, "", 100000 + m}; endfor
  endfor
  if (include_knn)
    k_values = [1 3 5 7 10 15 21 31 51 75 100]; weights = {"equal", "inverse", "squaredinverse"};
    for k = k_values
      for w = 1:numel (weights)
        for v = 1:numel (variants)
          plan(end + 1, :) = {["KNN k=", num2str(k), " ", weights{w}], v, "knn", k, weights{w}, 20261017};
        endfor
      endfor
    endfor
  endif
endfunction

function mdl = train_classifier_binary (model_name, tbl, response, svm_tolerance)
  p = columns (tbl) - 1;
  switch (model_name)
    case "Fine Tree", mdl = fitctree (tbl, response, "MaxNumSplits", 100);
    case "Medium Tree", mdl = fitctree (tbl, response, "MaxNumSplits", 20);
    case "Coarse Tree", mdl = fitctree (tbl, response, "MaxNumSplits", 4);
    case "Kernel Naive Bayes"
      distributions = repmat ({"kernel"}, 1, p); names = tbl.Properties.VariableNames(1:end-1);
      candidate_type_index = find (strcmp (names, "candidate_type"));
      if (! isempty (candidate_type_index)), distributions{candidate_type_index} = "mvmn"; endif
      mdl = fitcnb (tbl, response, "DistributionNames", distributions);
    case "Linear SVM", mdl = fitcecoc (tbl, response, "Learners", templateSVM ("KernelFunction", "linear", "Standardize", true, "Tolerance", svm_tolerance), "Coding", "onevsone");
    case "Quadratic SVM", mdl = fitcecoc (tbl, response, "Learners", templateSVM ("KernelFunction", "polynomial", "PolynomialOrder", 2, "Standardize", true, "Tolerance", svm_tolerance), "Coding", "onevsone");
    case "Cubic SVM", mdl = fitcecoc (tbl, response, "Learners", templateSVM ("KernelFunction", "polynomial", "PolynomialOrder", 3, "Standardize", true, "Tolerance", svm_tolerance), "Coding", "onevsone");
    case "Fine Gaussian SVM", mdl = fitcecoc (tbl, response, "Learners", templateSVM ("KernelFunction", "gaussian", "KernelScale", sqrt (p) / 4, "Standardize", true, "Tolerance", svm_tolerance), "Coding", "onevsone");
    case "Medium Gaussian SVM", mdl = fitcecoc (tbl, response, "Learners", templateSVM ("KernelFunction", "gaussian", "KernelScale", sqrt (p), "Standardize", true, "Tolerance", svm_tolerance), "Coding", "onevsone");
    case "Coarse Gaussian SVM", mdl = fitcecoc (tbl, response, "Learners", templateSVM ("KernelFunction", "gaussian", "KernelScale", 4 * sqrt (p), "Standardize", true, "Tolerance", svm_tolerance), "Coding", "onevsone");
    case "SVM Kernel", mdl = fitcecoc (tbl, response, "Learners", templateKernel ("Learner", "svm", "Standardize", true), "Coding", "onevsone");
    case "Logistic Regression Kernel", mdl = fitcecoc (tbl, response, "Learners", templateKernel ("Learner", "logistic", "Standardize", true), "Coding", "onevsone");
    case "Boosted Trees", mdl = fitcensemble (tbl, response, "Method", "AdaBoostM1", "Learners", templateTree ("MaxNumSplits", 20), "NumLearningCycles", 30, "LearnRate", .1);
    case "Bagged Trees", mdl = fitcensemble (tbl, response, "Method", "Bag", "Learners", templateTree ("NumVariablesToSample", "all"), "NumLearningCycles", 30);
    case "RUSBoosted Trees", mdl = fitcensemble (tbl, response, "Method", "RUSBoost", "Learners", templateTree ("MaxNumSplits", 20), "NumLearningCycles", 30, "LearnRate", .1);
    otherwise, error ("Tundmatu mudel: %s", model_name);
  endswitch
endfunction

function mdl = train_knn_binary (x, y, k, weight)
  mdl = fitcknn (x, y, "NumNeighbors", k, "Distance", "euclidean", "DistanceWeight", weight, ...
                 "Standardize", false, "NSMethod", "exhaustive", "BreakTies", "smallest", "IncludeTies", false);
endfunction

function [x, z, groups, encoding] = encode_knn_binary (train, test, predictors)
  x = zeros (size (train, 1), 0); z = zeros (size (test, 1), 0); groups = []; encoding = struct ();
  for j = 1:numel (predictors)
    name = predictors{j};
    if (strcmp (name, "candidate_type"))
      levels = unique (train.(name)); a = zeros (size (train, 1), numel (levels) + 1); b = zeros (size (test, 1), numel (levels) + 1);
      for l = 1:numel (levels), a(:, l) = strcmp (train.(name), levels{l}); b(:, l) = strcmp (test.(name), levels{l}); endfor
      b(:, end) = ! ismember (test.(name), levels); encoding.Categories = levels;
    else
      mu = mean (train.(name)); sigma = std (train.(name)); if (sigma == 0), sigma = 1; endif
      a = (train.(name) - mu) / sigma; b = (test.(name) - mu) / sigma; encoding.(name) = [mu sigma];
    endif
    x = [x a]; z = [z b]; groups = [groups repmat(j, 1, columns(a))];
  endfor
endfunction

function labels = numeric_labels (values)
  if (iscell (values)), labels = cellfun (@str2double, values); else labels = values; endif
  labels = labels(:); assert (all (ismember (labels, [0; 1])), "Ennustus ei ole binaarne 0/1.");
endfunction

function [overall, metrics, c, safety] = score_binary_predictions (actual, predicted)
  actual = actual(:); predicted = predicted(:); c = zeros (2, 2);
  for a = 0:1, for b = 0:1, c(a + 1, b + 1) = sum (actual == a & predicted == b); endfor; endfor
  tp = diag (c); support = sum (c, 2); fn = support - tp; fp = sum (c, 1)' - tp; tn = sum (c(:)) - tp - fn - fp;
  precision = safe_ratio_binary (tp, tp + fp); recall = safe_ratio_binary (tp, tp + fn); fpr = safe_ratio_binary (fp, fp + tn);
  fnr = safe_ratio_binary (fn, fn + tp); specificity = safe_ratio_binary (tn, tn + fp); f1 = safe_ratio_binary (2 * tp, 2 * tp + fp + fn);
  metrics = [support tp fp tn fn precision recall f1 fpr fnr specificity];
  overall = [sum(tp) / sum(c(:)), mean(f1), mean(recall), sum(f1 .* support) / sum(support)];
  % 0-haru tähendab automaatset lõppotsust; NPV mõõdab selle haru õigsust.
  automated = sum(predicted == 0); automated_errors = sum(actual == 1 & predicted == 0);
  safety = [recall(2), fnr(2), safe_ratio_binary(c(1,1), automated), automated / numel(actual)];
endfunction

function value = safe_ratio_binary (a, b), value = a ./ b; value(b == 0) = NaN; endfunction

function files = initialise_binary_outputs (folder, cohort)
  files.models = fullfile (folder, ["models_", cohort, "_inimsekkumine_octave.csv"]);
  files.perclass = fullfile (folder, ["perclass_", cohort, "_inimsekkumine_octave.csv"]);
  files.confusion = fullfile (folder, ["confusion_", cohort, "_inimsekkumine_octave.csv"]);
  files.predictions = fullfile (folder, ["predictions_", cohort, "_inimsekkumine_octave.csv"]);
  files.errors = fullfile (folder, ["errors_", cohort, "_inimsekkumine_octave.csv"]);
  write_binary_header (files.models, {"Model", "Variant", "Family", "TrainingAccuracy", "Accuracy", "MacroF1", "BalancedAccuracy", "WeightedF1", "Recall1_TPR", "FNR1", "NPV0_AutomaticBranchCorrectness", "AutomaticBranchShare", "TestRows", "Status"});
  write_binary_header (files.perclass, {"Model", "Variant", "Class", "Support", "TP", "FP", "TN", "FN", "Precision", "Recall_TPR", "F1", "FPR", "FNR", "Specificity_TNR"});
  write_binary_header (files.confusion, {"Model", "Variant", "Actual", "Predicted", "Count"});
  write_binary_header (files.predictions, {"Model", "Variant", "Process", "Candidate", "Actual", "Predicted"});
  write_binary_header (files.errors, {"Model", "Variant", "Error"});
endfunction

function validate_binary_data (train, test, predictors, response, cohort)
  required = [{"process", "candidate"}, predictors, {response}];
  assert (all (ismember (required, train.Properties.VariableNames)), "Treeningfailist puuduvad nõutud veerud.");
  assert (all (ismember (required, test.Properties.VariableNames)), "Testfailist puuduvad nõutud veerud.");
  assert (all (ismember (train.(response), [0; 1])) && all (ismember (test.(response), [0; 1])), "Vastuseväärtused peavad olema 0 või 1.");
  assert (all (ismember ([0; 1], unique (train.(response)))) && all (ismember ([0; 1], unique (test.(response)))), "Mõlemad klassid peavad olema treeningus ja testis.");
  assert (isempty (intersect (train.candidate, test.candidate)), "Treening ja test sisaldavad samu kandidaate.");
  assert (all (ismember (test.candidate_type, unique (train.candidate_type))), "Testis on treeningus puuduv candidate_type.");
  assert (ismember (cohort, {"b1", "b2", "c1", "d1", "x1", "y1"}), "Tundmatu kohort.");
endfunction

function write_binary_header (path, fields)
  fid = fopen (path, "w"); assert (fid >= 0, "CSV faili loomine ebaõnnestus: %s", path); write_binary_line (fid, fields); fclose (fid);
endfunction
function append_csv_binary (path, fields)
  fid = fopen (path, "a"); assert (fid >= 0, "CSV faili avamine ebaõnnestus: %s", path); write_binary_line (fid, fields); fclose (fid);
endfunction
function write_binary_line (fid, fields)
  escaped = cell (1, numel (fields));
  for i = 1:numel (fields)
    value = fields{i}; if (isnumeric (value)), if (isnan (value)), text = ""; else text = sprintf ("%.15g", value); endif; else text = char (value); endif
    text = strrep (text, char (34), char ([34 34])); escaped{i} = sprintf ('"%s"', text);
  endfor
  fprintf (fid, "%s\n", strjoin (escaped, ","));
endfunction
