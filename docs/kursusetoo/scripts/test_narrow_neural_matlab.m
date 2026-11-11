function outputs = test_narrow_neural_matlab(trainingFile, testFiles, repetitions)
%TEST_NARROW_NEURAL_MATLAB Repeat a one-layer narrow neural-network test.
%
% With no arguments, runs ten independent fits for every fixed B/C/D/X/Y
% cohort found in this script's own directory.
%
%   outputs = test_narrow_neural_matlab
%   check = test_narrow_neural_matlab("check")
%   outputs = test_narrow_neural_matlab( ...
%       "training_data_x.csv", "test_data_x1.csv", 10)
%
% The network is a fitcnet model with one 10-unit ReLU hidden layer and
% standardized numeric predictors.  The final three-unit softmax output
% layer is created by fitcnet from the three decision classes.
%
% A single, fixed, stratified five-fold partition is used for every run.
% Thus runs differ by their random network initialization, not by a
% different validation fold assignment.  Each run is fitted once to all
% training rows for external-test predictions, and five additional times
% for the validation prediction.
%
% The no-argument run requires these exact CSV file names beside this .m
% file: training_data_b/c/d/x/y.csv; test1_data_b.csv; test2_data_b.csv;
% test_data_c1.csv; test_data_d1.csv; test_data_x1.csv; test_data_y1.csv.

if nargin == 0
    outputs = runAllFixedCohorts(fileparts(mfilename("fullpath")), 10, false);
    return
end
if nargin == 1 && string(trainingFile) == "check"
    outputs = runAllFixedCohorts(fileparts(mfilename("fullpath")), 10, true);
    return
end
if nargin < 3 || isempty(repetitions)
    repetitions = 10;
end
assert(nargin >= 2 && strlength(string(trainingFile)) > 0 && ~isempty(testFiles), ...
    "Ühe andmejaotuse käivitamiseks anna treeningfail, testfail(id) ja soovi korral korduste arv.");

testFiles = string(testFiles(:));
assert(repetitions >= 1 && repetitions == floor(repetitions), ...
    "Korduste arv peab olema positiivne täisarv.");

predictors = ["duration_s"; "words"; "show_speaker_count"; "candidate_type"; ...
    "internal_speaker_change_count"; "distinct_speaker_count"; ...
    "dominant_speaker_coverage"; "nearest_change_edge_ratio"];
classes = ["ACCEPTED"; "MODIFIED"; "REJECTED"];

train = readtable(trainingFile, TextType="string", VariableNamingRule="preserve");
validateTable(train, predictors, classes, "Treeningfail");

tests = cell(numel(testFiles), 1);
for t = 1:numel(testFiles)
    tests{t} = readtable(testFiles(t), TextType="string", VariableNamingRule="preserve");
    validateTable(tests{t}, predictors, classes, "Testfail " + testFiles(t));
end

% All categorical dictionaries originate only from the training data.
levels = unique(string(train.candidate_type), "sorted");
assert(~isempty(levels), "Treeningandmetes puudub candidate_type.");
train.candidate_type = categorical(train.candidate_type, levels);
train.decision = categorical(train.decision, classes);
for t = 1:numel(tests)
    assert(all(ismember(string(tests{t}.candidate_type), levels)), ...
        "Testfailis %s on treeningus puuduv candidate_type.", testFiles(t));
    tests{t}.candidate_type = categorical(tests{t}.candidate_type, levels);
    tests{t}.decision = categorical(tests{t}.decision, classes);
end

% This seed fixes only the validation partition.  Run seeds below control
% each independent network initialization and optimization path.
partitionSeed = 20261021;
previousRng = rng;
cleanup = onCleanup(@() rng(previousRng)); %#ok<NASGU>
rng(partitionSeed, "twister");
cvp = cvpartition(train.decision, "KFold", 5);

% This is the explicit architecture under test, not hyperparameter search.
networkOptions = struct( ...
    "LayerSizes", 10, ...
    "Activations", "relu", ...
    "Standardize", true, ...
    "PartitionSeed", partitionSeed, ...
    "RunSeeds", (1:repetitions)');

base = fileparts(string(trainingFile));
if strlength(base) == 0, base = string(pwd); end
[~, testFileName, ~] = fileparts(testFiles(1));
tag = erase(string(testFileName), "test_data_");
folder = string(tempname(char(base))) + "_" + tag + "_narrow_neural_matlab";
mkdir(folder);
mkdir(fullfile(folder, "models"));
fprintf("Tulemuste kaust: %s\n", folder);

matlabVersion = version;
toolboxes = ver;
copyfile(mfilename("fullpath") + ".m", fullfile(folder, "test_narrow_neural_matlab.m"));
save(fullfile(folder, "settings.mat"), "trainingFile", "testFiles", ...
    "repetitions", "predictors", "classes", "levels", "networkOptions", ...
    "cvp", "matlabVersion", "toolboxes");

runs = emptyRunsTable();
perClass = emptyPerClassTable();
confusion = emptyConfusionTable();
predictions = emptyPredictionsTable();
errors = table(strings(0,1), zeros(0,1), strings(0,1), ...
    'VariableNames', ["Dataset","Run","Error"]);

for run = 1:repetitions
    seed = networkOptions.RunSeeds(run);
    fprintf("[%d/%d] Narrow Neural Network, seed %d\n", run, repetitions, seed);
    try
        % Full fit is used only for external-test predictions.
        rng(seed, "twister");
        mdl = fitcnet(train(:, cellstr([predictors; "decision"])), "decision", ...
            LayerSizes=networkOptions.LayerSizes, ...
            Activations=networkOptions.Activations, ...
            Standardize=networkOptions.Standardize);

        % Cross-validation refits the same specified network on each fold.
        rng(seed, "twister");
        cvMdl = crossval(mdl, CVPartition=cvp);
        validationPrediction = string(kfoldPredict(cvMdl));
        [validationOverall, validationMetrics, validationC] = ...
            scorePredictions(string(train.decision), validationPrediction, classes);

        save(fullfile(folder, "models", sprintf("narrow_run_%03d.mat", run)), ...
            "mdl", "cvMdl", "seed", "networkOptions", "predictors", "classes");

        runs = [runs; makeRunRow("Validation", run, seed, validationOverall, height(train), "OK")]; %#ok<AGROW>
        perClass = [perClass; makePerClassRows("Validation", run, validationMetrics, classes)]; %#ok<AGROW>
        confusion = [confusion; makeConfusionRows("Validation", run, validationC, classes)]; %#ok<AGROW>

        for t = 1:numel(tests)
            predicted = string(predict(mdl, tests{t}(:, cellstr(predictors))));
            actual = string(tests{t}.decision);
            [overall, metrics, C] = scorePredictions(actual, predicted, classes);
            dataset = datasetName(testFiles(t));
            runs = [runs; makeRunRow(dataset, run, seed, overall, height(tests{t}), "OK")]; %#ok<AGROW>
            perClass = [perClass; makePerClassRows(dataset, run, metrics, classes)]; %#ok<AGROW>
            confusion = [confusion; makeConfusionRows(dataset, run, C, classes)]; %#ok<AGROW>
            predictions = [predictions; table( ...
                repmat(dataset, height(tests{t}), 1), repmat(run, height(tests{t}), 1), ...
                tests{t}.process, tests{t}.candidate, actual, predicted, ...
                'VariableNames', predictions.Properties.VariableNames)]; %#ok<AGROW>
        end
    catch exception
        errors = [errors; {"all", run, string(getReport(exception, "extended", "hyperlinks", "off"))}]; %#ok<AGROW>
        runs = [runs; makeRunRow("FAILED", run, seed, nan(1,4), 0, "FAILED")]; %#ok<AGROW>
        warning("Narrow Neural Network run %d failed: %s", run, exception.message);
    end

    % Checkpoint after every run: completed runs remain available if MATLAB stops.
    outputs = writeOutputs(folder, runs, perClass, confusion, predictions, errors);
end

outputs.OutputFolder = folder;
save(fullfile(folder, "results.mat"), "outputs", "networkOptions", "cvp");
disp(outputs.Runs);
fprintf("Valmis. Õnnestus %d/%d kordust.\n", ...
    numel(unique(outputs.Runs.Run(outputs.Runs.Status == "OK"))), repetitions);
end

function validateTable(tbl, predictors, classes, description)
required = ["process"; "candidate"; predictors; "decision"];
assert(isempty(setdiff(required, string(tbl.Properties.VariableNames))), ...
    "%s: puuduvad nõutud veerud.", description);
assert(all(ismember(string(tbl.decision), classes)), ...
    "%s: decision sisaldab tundmatut klassi.", description);
assert(~any(ismissing(tbl.candidate_type)), "%s: candidate_type sisaldab puuduvat väärtust.", description);
for j = [1:3 5:8]
    assert(isnumeric(tbl.(predictors(j))) && all(isfinite(tbl.(predictors(j)))), ...
        "%s: vigane atribuut %s.", description, predictors(j));
end
end

function [overall, metrics, C] = scorePredictions(actual, predicted, classes)
C = zeros(3);
for a = 1:3
    for b = 1:3
        C(a,b) = sum(actual == classes(a) & predicted == classes(b));
    end
end
tp = diag(C); support = sum(C, 2); fn = support - tp;
fp = sum(C, 1)' - tp; tn = sum(C, "all") - tp - fn - fp;
precision = ratio(tp, tp + fp); recall = ratio(tp, tp + fn);
f1 = ratio(2 * tp, 2 * tp + fp + fn);
fpr = ratio(fp, fp + tn); fnr = ratio(fn, fn + tp);
specificity = ratio(tn, tn + fp);
metrics = [support, tp, fp, tn, fn, precision, recall, f1, fpr, fnr, specificity];
overall = [sum(tp) / sum(C, "all"), mean(f1), mean(recall), ...
    sum(f1 .* support) / sum(support)];
end

function value = ratio(a, b)
value = a ./ b;
value(b == 0) = nan;
end

function runs = emptyRunsTable()
runs = table(strings(0,1), zeros(0,1), zeros(0,1), zeros(0,1), zeros(0,1), ...
    zeros(0,1), zeros(0,1), zeros(0,1), strings(0,1), ...
    'VariableNames', ["Dataset","Run","Seed","Accuracy","MacroF1", ...
    "BalancedAccuracy","WeightedF1","Rows","Status"]);
end

function row = makeRunRow(dataset, run, seed, overall, rows, status)
row = table(string(dataset), run, seed, overall(1), overall(2), overall(3), ...
    overall(4), rows, string(status), 'VariableNames', ...
    ["Dataset","Run","Seed","Accuracy","MacroF1","BalancedAccuracy", ...
    "WeightedF1","Rows","Status"]);
end

function perClass = emptyPerClassTable()
perClass = table(strings(0,1), zeros(0,1), strings(0,1), zeros(0,1), ...
    zeros(0,1), zeros(0,1), zeros(0,1), zeros(0,1), zeros(0,1), ...
    zeros(0,1), zeros(0,1), zeros(0,1), zeros(0,1), zeros(0,1), ...
    'VariableNames', ["Dataset","Run","Class","Support","TP","FP","TN", ...
    "FN","Precision","Recall_TPR","F1","FPR","FNR","Specificity_TNR"]);
end

function rows = makePerClassRows(dataset, run, metrics, classes)
rows = table(repmat(string(dataset),3,1), repmat(run,3,1), classes, ...
    metrics(:,1), metrics(:,2), metrics(:,3), metrics(:,4), metrics(:,5), ...
    metrics(:,6), metrics(:,7), metrics(:,8), metrics(:,9), metrics(:,10), metrics(:,11), ...
    'VariableNames', ["Dataset","Run","Class","Support","TP","FP","TN", ...
    "FN","Precision","Recall_TPR","F1","FPR","FNR","Specificity_TNR"]);
end

function confusion = emptyConfusionTable()
confusion = table(strings(0,1), zeros(0,1), strings(0,1), strings(0,1), zeros(0,1), ...
    'VariableNames', ["Dataset","Run","Actual","Predicted","Count"]);
end

function rows = makeConfusionRows(dataset, run, C, classes)
rows = emptyConfusionTable();
for a = 1:3
    for b = 1:3
        rows = [rows; {string(dataset), run, classes(a), classes(b), C(a,b)}]; %#ok<AGROW>
    end
end
end

function predictions = emptyPredictionsTable()
predictions = table(strings(0,1), zeros(0,1), zeros(0,1), zeros(0,1), ...
    strings(0,1), strings(0,1), 'VariableNames', ...
    ["Dataset","Run","Process","Candidate","Actual","Predicted"]);
end

function outputs = writeOutputs(folder, runs, perClass, confusion, predictions, errors)
outputs = struct;
outputs.Runs = runs;
outputs.PerClass = perClass;
outputs.Confusion = confusion;
outputs.Predictions = predictions;
outputs.Errors = errors;
writetable(runs, fullfile(folder, "runs.csv"));
writetable(perClass, fullfile(folder, "per_class.csv"));
writetable(confusion, fullfile(folder, "confusion.csv"));
writetable(predictions, fullfile(folder, "predictions.csv"));
writetable(errors, fullfile(folder, "errors.csv"));
end

function name = datasetName(file)
[~, name, ~] = fileparts(file);
name = string(name);
end

function allOutputs = runAllFixedCohorts(dataFolder, repetitions, preflightOnly)
% The mapping below follows the fixed experimental definitions:
% B -> B1 and B2; C -> C1; D -> D1; X -> X1; Y -> Y1.
plans = struct( ...
    "Cohort", {"B", "C", "D", "X", "Y"}, ...
    "Training", {"training_data_b.csv", "training_data_c.csv", ...
                 "training_data_d.csv", "training_data_x.csv", "training_data_y.csv"}, ...
    "Tests", {{"test1_data_b.csv", "test2_data_b.csv"}, {"test_data_c1.csv"}, ...
              {"test_data_d1.csv"}, {"test_data_x1.csv"}, {"test_data_y1.csv"}});

% Check the complete fixed input set before fitting any model.
required = [string({plans.Training}), "test1_data_b.csv", "test2_data_b.csv", ...
    "test_data_c1.csv", "test_data_d1.csv", "test_data_x1.csv", "test_data_y1.csv"];
missing = required(~isfile(fullfile(dataFolder, required)));
assert(isempty(missing), "Puuduvad nõutud CSV-failid: %s", strjoin(missing, ", "));

% Fixed row counts are checked before any fitting.  They are the counts
% documented for B1/B2/C1/D1/X1/Y1 and their respective training sets.
expectedFileNames = [ ...
    "training_data_b.csv"; "test1_data_b.csv"; "test2_data_b.csv"; ...
    "training_data_c.csv"; "test_data_c1.csv"; ...
    "training_data_d.csv"; "test_data_d1.csv"; ...
    "training_data_x.csv"; "test_data_x1.csv"; ...
    "training_data_y.csv"; "test_data_y1.csv"];
expectedRows = [1006; 488; 337; 1277; 554; 1283; 548; 1281; 550; 1281; 550];
for i = 1:numel(expectedFileNames)
    verifyFixedCsv(fullfile(dataFolder, expectedFileNames(i)), expectedRows(i));
end

predictors = ["duration_s"; "words"; "show_speaker_count"; "candidate_type"; ...
    "internal_speaker_change_count"; "distinct_speaker_count"; ...
    "dominant_speaker_coverage"; "nearest_change_edge_ratio"];
classes = ["ACCEPTED"; "MODIFIED"; "REJECTED"];
for i = 1:numel(plans)
    verifyCohortInputs(dataFolder, plans(i), predictors, classes);
end

% Create every output-table schema during the no-write preflight as well.
addCohort(emptyRunsTable(), "B");
addCohort(emptyPerClassTable(), "B");
addCohort(emptyConfusionTable(), "B");
addCohort(emptyPredictionsTable(), "B");
table(strings(0,1), zeros(0,1), strings(0,1), ...
    'VariableNames', ["Dataset","Run","Error"]);

if preflightOnly
    allOutputs = struct("PreflightOnly", true, "Status", "OK", ...
        "Repetitions", repetitions, "Cohorts", string({plans.Cohort}));
    fprintf("Eelkontroll OK: kõik 11 CSV-faili, ridade arvud, atribuudid ja tabeliskeemid on korras. Mudelit ei treenitud.\n");
    return
end

masterFolder = string(tempname(char(dataFolder))) + "_all_narrow_neural_matlab";
mkdir(masterFolder);
copyfile(mfilename("fullpath") + ".m", fullfile(masterFolder, "test_narrow_neural_matlab.m"));

allRuns = table();
allPerClass = table();
allConfusion = table();
allErrors = table();
allOutputs = struct;
allOutputs.OutputFolder = masterFolder;
allOutputs.Repetitions = repetitions;

for i = 1:numel(plans)
    cohort = string(plans(i).Cohort);
    trainingFile = fullfile(dataFolder, plans(i).Training);
    testFiles = fullfile(dataFolder, string(plans(i).Tests));
    fprintf("\n=== %s: %s ===\n", cohort, strjoin(string(plans(i).Tests), ", "));
    outputs = test_narrow_neural_matlab(trainingFile, testFiles, repetitions);
    allOutputs.(cohort) = outputs;
    if i == 1
        allRuns = addCohort(outputs.Runs, cohort);
        allPerClass = addCohort(outputs.PerClass, cohort);
        allConfusion = addCohort(outputs.Confusion, cohort);
        allErrors = addCohort(outputs.Errors, cohort);
    else
        allRuns = [allRuns; addCohort(outputs.Runs, cohort)]; %#ok<AGROW>
        allPerClass = [allPerClass; addCohort(outputs.PerClass, cohort)]; %#ok<AGROW>
        allConfusion = [allConfusion; addCohort(outputs.Confusion, cohort)]; %#ok<AGROW>
        allErrors = [allErrors; addCohort(outputs.Errors, cohort)]; %#ok<AGROW>
    end
    writetable(allRuns, fullfile(masterFolder, "all_runs.csv"));
    writetable(allPerClass, fullfile(masterFolder, "all_per_class.csv"));
    writetable(allConfusion, fullfile(masterFolder, "all_confusion.csv"));
    writetable(allErrors, fullfile(masterFolder, "all_errors.csv"));
end

allOutputs.Runs = allRuns;
allOutputs.PerClass = allPerClass;
allOutputs.Confusion = allConfusion;
allOutputs.Errors = allErrors;
save(fullfile(masterFolder, "all_results.mat"), "allOutputs", "plans");
fprintf("\nKõik B/C/D/X/Y katsed valmis. Koondtulemused: %s\n", masterFolder);
end

function verifyCohortInputs(dataFolder, plan, predictors, classes)
train = readtable(fullfile(dataFolder, plan.Training), ...
    TextType="string", VariableNamingRule="preserve");
validateTable(train, predictors, classes, "Treeningfail " + string(plan.Training));
levels = unique(string(train.candidate_type), "sorted");
for testName = string(plan.Tests)
    test = readtable(fullfile(dataFolder, testName), ...
        TextType="string", VariableNamingRule="preserve");
    validateTable(test, predictors, classes, "Testfail " + testName);
    assert(all(ismember(string(test.candidate_type), levels)), ...
        "Testfailis %s on treeningus puuduv candidate_type.", testName);
end
end

function verifyFixedCsv(file, expectedRows)
tbl = readtable(file, TextType="string", VariableNamingRule="preserve");
assert(height(tbl) == expectedRows, ...
    "%s: oodati %d andmerida, leiti %d.", file, expectedRows, height(tbl));
end

function tableWithCohort = addCohort(tbl, cohort)
cohortColumn = table(repmat(string(cohort), height(tbl), 1), ...
    'VariableNames', "Cohort");
tableWithCohort = [cohortColumn tbl];
end
