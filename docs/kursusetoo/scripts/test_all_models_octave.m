function outputs = test_all_models_octave (training_file, test_file, selected_models)
  % GNU Octave implementation of the fixed Test1, Test2, C1, D1, X1 or Y1 experiment.
  % Run from project root:
  % octave11 --eval "addpath('docs/kursusetoo/scripts'); test_all_models_octave('log/training_data_b.csv','log/test1_data_b.csv')"
  % This is a separate Octave experiment, not a claim of MATLAB-identical output.

  pkg load statistics;
  if (nargin < 1), training_file = "log/training_data_b.csv"; endif
  if (nargin < 2), test_file = "log/test1_data_b.csv"; endif
  if (nargin < 3), selected_models = {}; endif
  if (! isempty (strfind (test_file, "test2_data_b.csv")))
    cohort = "test2";
  elseif (! isempty (strfind (test_file, "test_data_c1.csv")))
    cohort = "c1";
  elseif (! isempty (strfind (test_file, "test_data_d1.csv")))
    cohort = "d1";
  elseif (! isempty (strfind (test_file, "test_data_x1.csv")))
    cohort = "x1";
  elseif (! isempty (strfind (test_file, "test_data_y1.csv")))
    cohort = "y1";
  else
    assert (! isempty (strfind (test_file, "test1_data_b.csv")), ...
            "Testfail peab olema fikseeritud Test1 või Test2 CSV.");
    cohort = "test1";
  endif

  train = readtable (training_file);
  test = readtable (test_file);
  test_rows = size (test, 1);
  predictors = {"duration_s", "words", "show_speaker_count", "candidate_type", ...
                "internal_speaker_change_count", "distinct_speaker_count", ...
                "dominant_speaker_coverage", "nearest_change_edge_ratio"};
  classes = {"ACCEPTED"; "MODIFIED"; "REJECTED"};
  % Octave Statistics passes its otherwise very strict 1e-6 default to
  % LIBSVM.  LIBSVM's documented default is 1e-3; use it explicitly so
  % standard SVM variants can terminate before their internal iteration cap.
  svm_tolerance = 1e-3;
  validate_frozen_cohorts (train, test, predictors, classes, cohort);
  if (! strcmp (cohort, "x1") && ! strcmp (cohort, "y1"))
    assert (isempty (intersect (train.process, test.process)), "Saated kattuvad!");
  endif
  assert (isempty (intersect (train.candidate, test.candidate)), "Kandidaadid kattuvad!");
  assert (all (ismember (test.candidate_type, unique (train.candidate_type))), ...
          "Testis on treeningus puuduv candidate_type.");

  [full_x, test_x, groups, encoding] = encode_knn (train, test, predictors);
  all_models = {"Fine Tree", "Medium Tree", "Coarse Tree", "Kernel Naive Bayes", ...
                "Linear SVM", "Quadratic SVM", "Cubic SVM", "Fine Gaussian SVM", ...
                "Medium Gaussian SVM", "Coarse Gaussian SVM", "SVM Kernel", ...
                "Logistic Regression Kernel", "Boosted Trees", "Bagged Trees", "RUSBoosted Trees"};
  if (isempty (selected_models))
    models = all_models;
    include_knn = true;
  else
    assert (iscell (selected_models) && all (ismember (selected_models, all_models)), ...
            "selected_models peab sisaldama ainult toetatud mitte-kNN mudelinimesid.");
    models = selected_models;
    include_knn = false;
  endif
  removed_sets = cell (1, 11);
  removed_sets{1} = [];
  for removal_index = 1:8
    removed_sets{removal_index + 1} = removal_index;
  endfor
  removed_sets{10} = [5 6];
  removed_sets{11} = 5:8;
  variants = [{"full"}, predictors, {"both_speaker_counts"}, {"all_four_new_features"}];
  plan = build_plan (models, variants, include_knn);
  if (include_knn)
    assert (size (plan, 1) == 498, "Täielik katseplaan peab sisaldama 498 varianti.");
  else
    assert (size (plan, 1) == numel (models) * 9, "Valitud mudelite katseplaan on vigane.");
  endif

  % Octave tempname() deliberately creates paths under /tmp.  Keep only its
  % unique basename, so the output remains in the project-mounted log folder.
  [~, run_name] = fileparts (tempname ());
  output_folder = fullfile (pwd (), "log", [run_name, "_", cohort, "_octave"]);
  [ok, msg] = mkdir (output_folder);
  assert (ok, "Tulemuste kausta loomine ebaõnnestus: %s", msg);
  files = initialise_outputs (output_folder, cohort);
  settings_file = fullfile (output_folder, ["settings_", cohort, "_octave.mat"]);
  octave_version = version ();
  save (settings_file, "training_file", "test_file", "predictors", "classes", ...
        "models", "selected_models", "include_knn", "variants", "removed_sets", "plan", "encoding", "octave_version", ...
        "svm_tolerance");
  % Source remains in docs/kursusetoo/scripts/test_all_models_octave.m; Octave's mfilename path
  % is not portable enough to copy it from inside a container run.
  fprintf ("Tulemuste kaust: %s\n", output_folder);

  successful = 0;
  failed = 0;
  for n = 1:size (plan, 1)
    model_name = plan{n, 1};
    variant_index = plan{n, 2};
    family = plan{n, 3};
    k = plan{n, 4};
    distance_weight = plan{n, 5};
    seed = plan{n, 6};
    variant = variants{variant_index};
    removed = removed_sets{variant_index};
    keep = ! ismember (1:8, removed);
    selected = predictors(keep);
    fprintf ("[%d/%d] %s / %s\n", n, size (plan, 1), model_name, variant);

    try
      rng (seed, "twister");
      if (strcmp (family, "knn"))
        columns = ! ismember (groups, removed);
        mdl = train_knn (full_x(:, columns), train.decision, k, distance_weight);
        predicted = predict (mdl, test_x(:, columns));
        fitted = predict (mdl, full_x(:, columns));
      else
        train_table = train(:, [selected, {"decision"}]);
        test_table = test(:, selected);
        mdl = train_classifier (model_name, train_table, svm_tolerance);
        predicted = predict (mdl, test_table);
        fitted = predict (mdl, train(:, selected));
      endif
      assert (iscell (predicted) && numel (predicted) == size (test, 1), ...
              "Mudeli ennustus ei ole nõutud kujul.");
      [overall, metrics, confusion] = score_predictions (test.decision, predicted, classes);
      training_accuracy = mean (strcmp (fitted, train.decision));
      append_csv_row (files.models, {model_name, variant, family, training_accuracy, ...
                                      overall(1), overall(2), overall(3), overall(4), ...
                                      test_rows, "OK"});
      for c = 1:3
        append_csv_row (files.perclass, {model_name, variant, classes{c}, ...
          metrics(c,1), metrics(c,2), metrics(c,3), metrics(c,4), metrics(c,5), ...
          metrics(c,6), metrics(c,7), metrics(c,8), metrics(c,9), metrics(c,10), metrics(c,11)});
        for d = 1:3
          append_csv_row (files.confusion, {model_name, variant, classes{c}, classes{d}, confusion(c, d)});
        endfor
      endfor
      for i = 1:size (test, 1)
        append_csv_row (files.predictions, {model_name, variant, test.process(i), ...
                                             test.candidate(i), test.decision{i}, predicted{i}});
      endfor
      successful += 1;
    catch err
      append_csv_row (files.errors, {model_name, variant, err.message});
      append_csv_row (files.models, {model_name, variant, family, NaN, NaN, NaN, NaN, NaN, test_rows, "FAILED"});
      fprintf (2, "FAILED: %s / %s: %s\n", model_name, variant, err.message);
      failed += 1;
    end_try_catch
  endfor
  close_outputs (files);
  outputs = struct ("OutputFolder", output_folder, "Successful", successful, "Failed", failed, ...
                    "Models", fullfile (output_folder, ["models_", cohort, "_octave.csv"]), ...
                    "PerClass", fullfile (output_folder, ["perclass_", cohort, "_octave.csv"]), ...
                    "Confusion", fullfile (output_folder, ["confusion_", cohort, "_octave.csv"]), ...
                    "Predictions", fullfile (output_folder, ["predictions_", cohort, "_octave.csv"]), ...
                    "Errors", fullfile (output_folder, ["errors_", cohort, "_octave.csv"]));
  save (fullfile (output_folder, ["results_", cohort, "_octave.mat"]), "outputs");
  fprintf ("Valmis. Õnnestus %d/%d; vigu %d.\n", successful, size (plan, 1), failed);
endfunction

function plan = build_plan (models, variants, include_knn)
  plan = cell (0, 6);
  for m = 1:numel (models)
    for v = 1:9
      plan(end + 1, :) = {models{m}, v, "other", NaN, "", 100000 + m};
    endfor
  endfor
  if (include_knn)
    k_values = [1 3 5 7 10 15 21 31 51 75 100];
    weights = {"equal", "inverse", "squaredinverse"};
    for k = k_values
      for w = 1:numel (weights)
        for v = 1:numel (variants)
          plan(end + 1, :) = {["KNN k=", num2str(k), " ", weights{w}], v, "knn", k, weights{w}, 20261017};
        endfor
      endfor
    endfor
  endif
endfunction

function mdl = train_classifier (model_name, tbl, svm_tolerance)
  p = columns (tbl) - 1;
  switch (model_name)
    case "Fine Tree", mdl = fitctree (tbl, "decision", "MaxNumSplits", 100);
    case "Medium Tree", mdl = fitctree (tbl, "decision", "MaxNumSplits", 20);
    case "Coarse Tree", mdl = fitctree (tbl, "decision", "MaxNumSplits", 4);
    case "Kernel Naive Bayes"
      distributions = repmat ({"kernel"}, 1, p);
      names = tbl.Properties.VariableNames(1:end-1);
      candidate_type_index = find (strcmp (names, "candidate_type"));
      if (! isempty (candidate_type_index))
        distributions{candidate_type_index} = "mvmn";
      endif
      mdl = fitcnb (tbl, "decision", "DistributionNames", distributions);
    case "Linear SVM"
      mdl = fitcecoc (tbl, "decision", "Learners", templateSVM ("KernelFunction", "linear", "Standardize", true, "Tolerance", svm_tolerance), "Coding", "onevsone");
    case "Quadratic SVM"
      mdl = fitcecoc (tbl, "decision", "Learners", templateSVM ("KernelFunction", "polynomial", "PolynomialOrder", 2, "Standardize", true, "Tolerance", svm_tolerance), "Coding", "onevsone");
    case "Cubic SVM"
      mdl = fitcecoc (tbl, "decision", "Learners", templateSVM ("KernelFunction", "polynomial", "PolynomialOrder", 3, "Standardize", true, "Tolerance", svm_tolerance), "Coding", "onevsone");
    case "Fine Gaussian SVM"
      mdl = fitcecoc (tbl, "decision", "Learners", templateSVM ("KernelFunction", "gaussian", "KernelScale", sqrt (p) / 4, "Standardize", true, "Tolerance", svm_tolerance), "Coding", "onevsone");
    case "Medium Gaussian SVM"
      mdl = fitcecoc (tbl, "decision", "Learners", templateSVM ("KernelFunction", "gaussian", "KernelScale", sqrt (p), "Standardize", true, "Tolerance", svm_tolerance), "Coding", "onevsone");
    case "Coarse Gaussian SVM"
      mdl = fitcecoc (tbl, "decision", "Learners", templateSVM ("KernelFunction", "gaussian", "KernelScale", 4 * sqrt (p), "Standardize", true, "Tolerance", svm_tolerance), "Coding", "onevsone");
    case "SVM Kernel"
      mdl = fitcecoc (tbl, "decision", "Learners", templateKernel ("Learner", "svm", "Standardize", true), "Coding", "onevsone");
    case "Logistic Regression Kernel"
      mdl = fitcecoc (tbl, "decision", "Learners", templateKernel ("Learner", "logistic", "Standardize", true), "Coding", "onevsone");
    case "Boosted Trees"
      mdl = fitcensemble (tbl, "decision", "Method", "AdaBoostM2", "Learners", templateTree ("MaxNumSplits", 20), "NumLearningCycles", 30, "LearnRate", .1);
    case "Bagged Trees"
      mdl = fitcensemble (tbl, "decision", "Method", "Bag", "Learners", templateTree ("NumVariablesToSample", "all"), "NumLearningCycles", 30);
    case "RUSBoosted Trees"
      mdl = fitcensemble (tbl, "decision", "Method", "RUSBoost", "Learners", templateTree ("MaxNumSplits", 20), "NumLearningCycles", 30, "LearnRate", .1);
    otherwise
      error ("Tundmatu mudel: %s", model_name);
  endswitch
endfunction

function mdl = train_knn (x, y, k, weight)
  mdl = fitcknn (x, y, "NumNeighbors", k, "Distance", "euclidean", ...
                 "DistanceWeight", weight, "Standardize", false, ...
                 "NSMethod", "exhaustive", "BreakTies", "smallest", "IncludeTies", false);
endfunction

function [x, z, groups, encoding] = encode_knn (train, test, predictors)
  x = zeros (size (train, 1), 0); z = zeros (size (test, 1), 0); groups = [];
  encoding = struct ();
  for j = 1:numel (predictors)
    name = predictors{j};
    if (strcmp (name, "candidate_type"))
      levels = unique (train.(name));
      a = zeros (size (train, 1), numel (levels) + 1);
      b = zeros (size (test, 1), numel (levels) + 1);
      for l = 1:numel (levels)
        a(:, l) = strcmp (train.(name), levels{l});
        b(:, l) = strcmp (test.(name), levels{l});
      endfor
      b(:, end) = ! ismember (test.(name), levels);
      encoding.Categories = levels;
    else
      mu = mean (train.(name)); sigma = std (train.(name));
      if (sigma == 0), sigma = 1; endif
      a = (train.(name) - mu) / sigma;
      b = (test.(name) - mu) / sigma;
      encoding.(name) = [mu sigma];
    endif
    x = [x a]; z = [z b]; groups = [groups repmat(j, 1, columns(a))];
  endfor
endfunction

function [overall, metrics, c] = score_predictions (actual, predicted, classes)
  c = zeros (3, 3);
  for a = 1:3
    for b = 1:3
      c(a, b) = sum (strcmp (actual, classes{a}) & strcmp (predicted, classes{b}));
    endfor
  endfor
  tp = diag (c); support = sum (c, 2); fn = support - tp;
  fp = sum (c, 1)' - tp; tn = sum (c(:)) - tp - fn - fp;
  precision = safe_ratio (tp, tp + fp); recall = safe_ratio (tp, tp + fn);
  fpr = safe_ratio (fp, fp + tn); fnr = safe_ratio (fn, fn + tp);
  specificity = safe_ratio (tn, tn + fp);
  f1 = safe_ratio (2 * tp, 2 * tp + fp + fn);
  metrics = [support tp fp tn fn precision recall f1 fpr fnr specificity];
  overall = [sum(tp) / sum(c(:)), mean(f1), mean(recall), sum(f1 .* support) / sum(support)];
endfunction

function value = safe_ratio (a, b)
  value = a ./ b;
  value(b == 0) = NaN;
endfunction

function files = initialise_outputs (folder, cohort)
  files.models = fullfile (folder, ["models_", cohort, "_octave.csv"]);
  files.perclass = fullfile (folder, ["perclass_", cohort, "_octave.csv"]);
  files.confusion = fullfile (folder, ["confusion_", cohort, "_octave.csv"]);
  files.predictions = fullfile (folder, ["predictions_", cohort, "_octave.csv"]);
  files.errors = fullfile (folder, ["errors_", cohort, "_octave.csv"]);
  write_csv_header (files.models, {"Model", "Variant", "Family", "TrainingAccuracy", "Accuracy", "MacroF1", "BalancedAccuracy", "WeightedF1", "TestRows", "Status"});
  write_csv_header (files.perclass, {"Model", "Variant", "Class", "Support", "TP", "FP", "TN", "FN", "Precision", "Recall_TPR", "F1", "FPR", "FNR", "Specificity_TNR"});
  write_csv_header (files.confusion, {"Model", "Variant", "Actual", "Predicted", "Count"});
  write_csv_header (files.predictions, {"Model", "Variant", "Process", "Candidate", "Actual", "Predicted"});
  write_csv_header (files.errors, {"Model", "Variant", "Error"});
endfunction

function write_csv_header (path, fields)
  fid = fopen (path, "w"); assert (fid >= 0, "CSV faili loomine ebaõnnestus: %s", path);
  write_csv_line (fid, fields); fclose (fid);
endfunction

function append_csv_row (path, fields)
  fid = fopen (path, "a"); assert (fid >= 0, "CSV faili avamine ebaõnnestus: %s", path);
  write_csv_line (fid, fields); fclose (fid);
endfunction

function write_csv_line (fid, fields)
  escaped = cell (1, numel (fields));
  for i = 1:numel (fields)
    value = fields{i};
    if (isnumeric (value))
      if (isnan (value)), text = ""; else text = sprintf ("%.15g", value); endif
    else
      text = char (value);
    endif
    text = strrep (text, char (34), char ([34 34]));
    escaped{i} = sprintf ('"%s"', text);
  endfor
  fprintf (fid, "%s\n", strjoin (escaped, ","));
endfunction

function close_outputs (files)
  % Files are appended and closed after each row so a stopped run retains output.
endfunction

function validate_frozen_cohorts (train, test, predictors, classes, cohort)
  required = [{"process", "candidate"}, predictors, {"decision"}];
  if (strcmp (cohort, "test2"))
    validate_test2_cohort (train, test, predictors, classes);
    return;
  endif
  if (strcmp (cohort, "c1") || strcmp (cohort, "d1"))
    validate_resplit_cohort (train, test, predictors, classes, cohort);
    return;
  endif
  if (strcmp (cohort, "x1") || strcmp (cohort, "y1"))
    validate_candidate_split_cohort (train, test, predictors, classes, cohort);
    return;
  endif
  assert (all (ismember (required, train.Properties.VariableNames)), "Treeningfailist puuduvad nõutud veerud.");
  assert (all (ismember (required, test.Properties.VariableNames)), "Testfailist puuduvad nõutud veerud.");
  assert (size(train, 1) == 1006, "Treeningfailis peab olema 1006 rida.");
  assert (size(test, 1) == 488, "Test1 failis peab olema 488 rida.");
  expected_train_processes = [31 32 34:42 44 47:50 53:55 57:59 61:67 69 71:72 75:78 81:82 84:86 88 90 93 95:101];
  assert (isequal (unique(train.process)', expected_train_processes), "Treeningfaili protsesside koosseis ei vasta fikseeritud valimile.");
  ranges = [14 130 170;15 179 221;16 222 249;18 296 334;19 335 373; ...
            20 374 395;21 396 406;22 407 444;23 445 462;24 463 504;25 505 528; ...
            26 567 611;27 612 649;28 650 671;29 672 709];
  expected = zeros (488, 2); cursor = 0;
  for i = 1:size(ranges, 1)
    ids = (ranges(i,2):ranges(i,3))'; count = numel(ids);
    expected(cursor + (1:count), :) = [repmat(ranges(i,1), count, 1), ids];
    cursor += count;
  endfor
  assert (isequal (sortrows ([test.process, test.candidate], [1 2]), expected), "Test1 kandidaadi-ID-d ei vasta fikseeritud valimile.");
  assert (sum (strcmp (test.decision, classes{1})) == 290 && sum (strcmp (test.decision, classes{2})) == 107 && sum (strcmp (test.decision, classes{3})) == 91, "Test1 klasside jaotus ei vasta fikseeritud valimile.");
  assert (sum (strcmp (train.decision, classes{1})) == 251 && sum (strcmp (train.decision, classes{2})) == 454 && sum (strcmp (train.decision, classes{3})) == 301, "Treeningu klasside jaotus ei vasta fikseeritud valimile.");
endfunction

function validate_candidate_split_cohort (train, test, predictors, classes, cohort)
  required = [{"process", "candidate"}, predictors, {"decision"}];
  assert (all (ismember (required, train.Properties.VariableNames)), "Treeningfailist puuduvad nõutud veerud.");
  assert (all (ismember (required, test.Properties.VariableNames)), "Testfailist puuduvad nõutud veerud.");
  assert (size(train, 1) + size(test, 1) == 1831, "Kandidaadipõhine jaotus peab koosnema 1 831 fikseeritud reast.");
  assert (! isempty (intersect (train.process, test.process)), "Kandidaadipõhises jaotuses peab vähemalt üks saade olema mõlemas pooles.");
  assert (isempty (intersect (train.candidate, test.candidate)), "Kandidaadipõhises jaotuses kattuvad kandidaadid.");
  assert (all (ismember (classes, unique (train.decision))) && all (ismember (classes, unique (test.decision))), ...
          "Kandidaadipõhises treeningus ja testis peab olema iga otsuseklass.");
  assert (all (ismember ([2; 3], unique (train.show_speaker_count))) && any (train.show_speaker_count >= 4), ...
          "Kandidaadipõhisest treeningust puudub 2-, 3- või 4+ osalejaga kandidaat.");
  assert (all (ismember ([2; 3], unique (test.show_speaker_count))) && any (test.show_speaker_count >= 4), ...
          "Kandidaadipõhisest testist puudub 2-, 3- või 4+ osalejaga kandidaat.");
  source_train = readtable ("log/training_data_b.csv");
  source_test1 = readtable ("log/test1_data_b.csv");
  source_test2 = readtable ("log/test2_data_b.csv");
  source_train = source_train(:, required);
  source_test1 = source_test1(:, required);
  source_test2 = source_test2(:, required);
  source = [source_train; source_test1; source_test2];
  combined = [train; test];
  assert (isequal (sortrows ([source.process, source.candidate], [1 2]), ...
                  sortrows ([combined.process, combined.candidate], [1 2])), ...
          "Kandidaadipõhine jaotus ei vasta täpselt B, Test1 ja Test2 fikseeritud ühendile.");
  [~, source_order] = sortrows ([source.process, source.candidate], [1 2]);
  [~, combined_order] = sortrows ([combined.process, combined.candidate], [1 2]);
  assert (all (strcmp (source.decision(source_order), combined.decision(combined_order))), ...
          "Kandidaadipõhises jaotuses on otsusmärgend muutunud.");
  assert (strcmp (cohort, "x1") || strcmp (cohort, "y1"), "Tundmatu kandidaadipõhine kohort.");
endfunction

function validate_resplit_cohort (train, test, predictors, classes, cohort)
  required = [{"process", "candidate"}, predictors, {"decision"}];
  assert (all (ismember (required, train.Properties.VariableNames)), "Treeningfailist puuduvad nõutud veerud.");
  assert (all (ismember (required, test.Properties.VariableNames)), "Testfailist puuduvad nõutud veerud.");
  assert (size(train, 1) + size(test, 1) == 1831, "C/D jaotus peab koosnema 1 831 fikseeritud reast.");
  assert (isempty (intersect (train.process, test.process)), "C/D jaotuses kattuvad saated.");
  assert (numel (unique ([train.process; test.process])) == 80, "C/D jaotuses peab olema 80 saadet.");
  assert (all (ismember (classes, unique (train.decision))) && all (ismember (classes, unique (test.decision))), ...
          "C/D treeningus ja testis peab olema iga otsuseklass.");
  assert (all (ismember ([2; 3], unique (train.show_speaker_count))) && any (train.show_speaker_count >= 4), ...
          "C/D treeningust puudub 2-, 3- või 4+ osalejaga saade.");
  assert (all (ismember ([2; 3], unique (test.show_speaker_count))) && any (test.show_speaker_count >= 4), ...
          "C/D testist puudub 2-, 3- või 4+ osalejaga saade.");
  source_train = readtable ("log/training_data_b.csv");
  source_test1 = readtable ("log/test1_data_b.csv");
  source_test2 = readtable ("log/test2_data_b.csv");
  source_train = source_train(:, required);
  source_test1 = source_test1(:, required);
  source_test2 = source_test2(:, required);
  source = [source_train; source_test1; source_test2];
  combined = [train; test];
  assert (isequal (sortrows ([source.process, source.candidate], [1 2]), ...
                  sortrows ([combined.process, combined.candidate], [1 2])), ...
          "C/D jaotus ei vasta täpselt B, Test1 ja Test2 fikseeritud ühendile.");
  [~, source_order] = sortrows ([source.process, source.candidate], [1 2]);
  [~, combined_order] = sortrows ([combined.process, combined.candidate], [1 2]);
  assert (all (strcmp (source.decision(source_order), combined.decision(combined_order))), ...
          "C/D jaotuses on otsusmärgend muutunud.");
  assert (all (ismember (test.candidate_type, unique (train.candidate_type))), ...
          "C/D testis on treeningus puuduv candidate_type.");
  assert (strcmp (cohort, "c1") || strcmp (cohort, "d1"), "Tundmatu C/D kohort.");
endfunction

function validate_test2_cohort (train, test, predictors, classes)
  required = [{"process", "candidate"}, predictors, {"decision"}];
  assert (all (ismember (required, train.Properties.VariableNames)), "Treeningfailist puuduvad nõutud veerud.");
  assert (all (ismember (required, test.Properties.VariableNames)), "Testfailist puuduvad nõutud veerud.");
  assert (size(train, 1) == 1006, "Treeningfailis peab olema 1006 rida.");
  assert (size(test, 1) == 337, "Test2 failis peab olema 337 rida.");
  expected_train_processes = [31 32 34:42 44 47:50 53:55 57:59 61:67 69 71:72 75:78 81:82 84:86 88 90 93 95:101];
  assert (isequal (unique(train.process)', expected_train_processes), "Treeningfaili protsesside koosseis ei vasta fikseeritud valimile.");
  ranges = [33 793 844;43 1240 1259;79 2126 2151;80 2152 2228;83 2255 2298; ...
            89 2418 2442;91 2472 2482;94 2553 2562;102 2694 2715;103 2716 2720; ...
            104 2721 2727;105 2728 2739;107 2770 2784;108 2785 2795];
  expected = zeros (337, 2); cursor = 0;
  for i = 1:size(ranges, 1)
    ids = (ranges(i,2):ranges(i,3))'; count = numel(ids);
    expected(cursor + (1:count), :) = [repmat(ranges(i,1), count, 1), ids];
    cursor += count;
  endfor
  assert (isequal (sortrows ([test.process, test.candidate], [1 2]), expected), "Test2 kandidaadi-ID-d ei vasta fikseeritud valimile.");
  assert (sum (strcmp (test.decision, classes{1})) == 62 && sum (strcmp (test.decision, classes{2})) == 151 && sum (strcmp (test.decision, classes{3})) == 124, "Test2 klasside jaotus ei vasta fikseeritud valimile.");
  assert (sum (strcmp (train.decision, classes{1})) == 251 && sum (strcmp (train.decision, classes{2})) == 454 && sum (strcmp (train.decision, classes{3})) == 301, "Treeningu klasside jaotus ei vasta fikseeritud valimile.");
endfunction
