function outputs = analyze_feature_value_knn(csvFile)
% KNN feature use and ablation, using only the full training CSV.
% Run from project root: outputs = analyze_feature_value_knn("log/training_data_b.csv")
% Numeric scaling is learned separately inside each training fold.
% candidate_type uses unscaled one-hot columns, permuted/removed as a group.
% No test data or Classification Learner session is required.

if nargin < 1
    [name, folder] = uigetfile('*.csv', 'Vali täielik training_data_b.csv');
    if isequal(name, 0), error('Faili ei valitud.'); end
    csvFile = fullfile(folder, name);
end
data = readtable(csvFile, TextType="string", VariableNamingRule="preserve");
predictors = ["duration_s"; "words"; "show_speaker_count"; "candidate_type"; ...
    "internal_speaker_change_count"; "distinct_speaker_count"; ...
    "dominant_speaker_coverage"; "nearest_change_edge_ratio"];
required = ["process"; predictors; "decision"];
missing = setdiff(required, string(data.Properties.VariableNames));
assert(isempty(missing), 'Puuduvad veerud: %s. Vali täielik treening-CSV.', strjoin(missing, ', '));
assert(isnumeric(data.process) && all(isfinite(data.process)), 'Vigane process veerg.');
assert(height(data) > 0, 'Tühi andmestik.');
classes = ["ACCEPTED"; "MODIFIED"; "REJECTED"];
y = string(data.decision);
assert(all(ismember(y, classes)), 'Tundmatu või puuduv decision.');
assert(numel(unique(y)) == 3, 'Treeningandmetes peavad olema kõik kolm klassi.');
assert(~any(ismissing(data.candidate_type)), 'Puuduv candidate_type.');
for j = [1:3 5:8]
    value = data.(predictors(j));
    assert(isnumeric(value) && iscolumn(value) && all(isfinite(value)), ...
        'Tunnus %s peab olema lõplik arv; puuduvaid väärtusi ei täideta automaatselt.', predictors(j));
end

previousRng = rng;
restoreRng = onCleanup(@() rng(previousRng)); %#ok<NASGU>
rng(20261017, 'twister');
fold = showFolds(data.process, 5); % Identical algorithm/seed to original script.
kValues = [1 3 5 7 10 15 21 31 51 75 100];
weights = ["equal", "inverse", "squaredinverse"];
numPermutations = 30;
assert(max(kValues) <= min(arrayfun(@(f) sum(fold ~= f), 1:5)), ...
    'Treeningfoldis on vähem ridu kui suurim k.');

% Preprocessing is fixed for all k, weighting and ablation comparisons.
[fullX, ~, fullGroups, fullEncoding] = encode(data, data, predictors);
parts = cell(5, 1);
for f = 1:5
    tr = fold ~= f; va = fold == f;
    assert(numel(unique(y(tr))) == 3, 'Foldi %d treeningosas puudub mõni klass.', f);
    [trainX, validX, groups, encoding] = encode(data(tr,:), data(va,:), predictors);
    parts{f} = struct('TrainX', trainX, 'ValidX', validX, ...
        'TrainY', categorical(y(tr), classes), 'Rows', va, ...
        'Groups', groups, 'Encoding', encoding);
end

% Individual removals, both low-ranked counts together, and all four new fields.
removals = arrayfun(@(j) j, 1:8, UniformOutput=false);
removals{9} = [5 6];
removals{10} = 5:8;
removalNames = [predictors; "both_speaker_counts"; "all_four_new_features"];

baseFolder = fileparts(string(csvFile));
if strlength(baseFolder) == 0, baseFolder = string(pwd); end
outputFolder = string(tempname(char(baseFolder))) + "_knn";
mkdir(outputFolder);
fprintf('Tulemuste kaust: %s\n', outputFolder);
modelRows = cell(0,10); importanceRows = cell(0,6); ablationRows = cell(0,9);
errorRows = cell(0,3);
foldRows = table((1:height(data))', data.process, fold, ...
    VariableNames={'ObservationIndex','Process','Fold'});
writetable(foldRows, fullfile(outputFolder, 'validation_folds_knn.csv'));
settings = struct('Predictors', predictors, 'KValues', kValues, ...
    'Weights', weights, 'NumPermutations', numPermutations, ...
    'Distance', "euclidean", 'NumericScaling', "training-fold mean and sample std", ...
    'CategoryScaling', "unscaled one-hot; unseen category has reserved indicator", ...
    'Seed', 20261017, 'SourceCSV', string(csvFile));
save(fullfile(outputFolder, 'settings_knn.mat'), 'settings', 'fullEncoding', 'parts', 'foldRows');

index = 0;
for k = kValues
    for weight = weights
        index = index + 1;
        modelName = "KNN k=" + k + " " + weight;
        fprintf('[%d/%d] %s\n', index, numel(kValues)*numel(weights), modelName);
        try
            cvPredicted = cvPredict(parts, height(data), k, weight, []);
            metrics = classificationMetrics(y, cvPredicted, classes);
            mdl = trainKNN(fullX, categorical(y, classes), k, weight);
            trainingAccuracy = mean(string(predict(mdl, fullX)) == y);
            modelRows(end+1,:) = {modelName,k,weight,metrics(1),trainingAccuracy, ...
                metrics(2),metrics(3),metrics(4),metrics(5),"OK"}; %#ok<AGROW>
        catch exception
            errorRows(end+1,:) = {modelName,"training",string(exception.message)}; %#ok<AGROW>
            warning('%s: %s', modelName, exception.message);
            writeResults(outputFolder, modelRows, importanceRows, ablationRows, errorRows);
            continue
        end

        % Resubstitution importance: same question as Training set in the UI.
        % It measures use, not generalisation. In particular k=1 can memorise rows.
        try
            changes = zeros(numPermutations, 8);
            rng(20261018, 'twister'); % Same permutations for every configuration.
            for j = 1:8
                columns = fullGroups == j;
                for repeat = 1:numPermutations
                    permutedX = fullX;
                    order = randperm(height(data));
                    permutedX(:,columns) = fullX(order,columns);
                    shuffledAccuracy = mean(string(predict(mdl, permutedX)) == y);
                    changes(repeat,j) = trainingAccuracy - shuffledAccuracy;
                end
            end
            means = mean(changes,1); deviations = std(changes,0,1);
            [~, order] = sort(means, 'descend');
            ranks = zeros(1,8); ranks(order) = 1:8;
            for j = 1:8
                importanceRows(end+1,:) = {modelName,predictors(j),means(j),deviations(j),ranks(j),"OK"}; %#ok<AGROW>
            end
        catch exception
            errorRows(end+1,:) = {modelName,"permutation",string(exception.message)}; %#ok<AGROW>
            warning('%s permutation: %s', modelName, exception.message);
        end

        for j = 1:numel(removals)
            try
                reducedPredicted = cvPredict(parts, height(data), k, weight, removals{j});
                reducedMetrics = classificationMetrics(y, reducedPredicted, classes);
                ablationRows(end+1,:) = {modelName,removalNames(j),metrics(1), ...
                    reducedMetrics(1),metrics(1)-reducedMetrics(1), ...
                    metrics(2),reducedMetrics(2),metrics(2)-reducedMetrics(2),"OK"}; %#ok<AGROW>
            catch exception
                errorRows(end+1,:) = {modelName,"remove " + removalNames(j),string(exception.message)}; %#ok<AGROW>
                warning('%s ablation %s: %s', modelName, removalNames(j), exception.message);
            end
        end
        % Checkpoint after each configuration; an interrupted run keeps completed results.
        writeResults(outputFolder, modelRows, importanceRows, ablationRows, errorRows);
    end
end
outputs = writeResults(outputFolder, modelRows, importanceRows, ablationRows, errorRows);
summaryRows = cell(0,11);
for j = 1:8
    ir = outputs.PermutationImportance(string(outputs.PermutationImportance.Predictor) == predictors(j),:);
    ar = outputs.Ablation(string(outputs.Ablation.RemovedPredictor) == predictors(j),:);
    summaryRows(end+1,:) = {predictors(j),j>=5,height(ir), ...
        mean(ir.ImportanceMean,'omitnan'),median(ir.ImportanceMean,'omitnan'), ...
        median(ir.Rank,'omitnan'),sum(ir.ImportanceMean>0),height(ar), ...
        mean(ar.AccuracyDrop,'omitnan'),median(ar.AccuracyDrop,'omitnan'), ...
        sum(ar.AccuracyDrop>0)}; %#ok<AGROW>
end
outputs.FeatureSummary = cell2table(summaryRows, VariableNames={ ...
    'Predictor','IsNew','SuccessfulImportanceModels','MeanPermutationImportance', ...
    'MedianPermutationImportance','MedianImportanceRank','ModelsUsingPredictor', ...
    'SuccessfulAblationModels','MeanAccuracyDrop','MedianAccuracyDrop','ModelsHelpedByPredictor'});
outputs.OutputFolder = outputFolder;
writetable(outputs.FeatureSummary, fullfile(outputFolder,'feature_value_summary_knn.csv'));
save(fullfile(outputFolder,'feature_value_results_knn.mat'), 'outputs', 'settings', 'foldRows');
disp(sortrows(outputs.Models,'CVAccuracy','descend'));
disp(outputs.FeatureSummary);
fprintf('Valmis: %s\nNegatiivne AccuracyDrop = eemaldamine parandas valideerimistäpsust.\n', outputFolder);
end

function mdl = trainKNN(X, y, k, weight)
mdl = fitcknn(X, y, NumNeighbors=k, Distance='euclidean', ...
    DistanceWeight=char(weight), Standardize=false, NSMethod='exhaustive', ...
    BreakTies='smallest', IncludeTies=false);
end

function result = cvPredict(parts, n, k, weight, removed)
result = strings(n,1);
for f = 1:numel(parts)
    part = parts{f};
    keep = ~ismember(part.Groups, removed);
    mdl = trainKNN(part.TrainX(:,keep), part.TrainY, k, weight);
    result(part.Rows) = string(predict(mdl, part.ValidX(:,keep)));
end
end

function [X, Z, groups, encoding] = encode(train, validation, predictors)
X = zeros(height(train),0); Z = zeros(height(validation),0); groups = [];
encoding = struct;
for j = 1:numel(predictors)
    name = predictors(j);
    if name == "candidate_type"
        levels = unique(string(train.(name)), 'sorted');
        trainLabels = string(train.(name)); validLabels = string(validation.(name));
        a = double(trainLabels == levels'); b = double(validLabels == levels');
        % Reserved unseen-category column; derived solely from training categories.
        a = [a, zeros(height(train),1)];
        b = [b, double(~ismember(validLabels,levels))];
        encoding.Categories = levels;
    else
        mu = mean(train.(name)); sigma = std(train.(name));
        if sigma == 0, sigma = 1; end
        a = (train.(name)-mu)/sigma; b = (validation.(name)-mu)/sigma;
        encoding.(name) = [mu sigma];
    end
    X = [X a]; Z = [Z b]; groups = [groups repmat(j,1,size(a,2))]; %#ok<AGROW>
end
end

function values = classificationMetrics(actual, predicted, classes)
C = zeros(3);
for a = 1:3
    for b = 1:3
        C(a,b) = sum(actual == classes(a) & predicted == classes(b));
    end
end
recall = diag(C)./max(sum(C,2),1);
precision = diag(C)./max(sum(C,1)',1);
f1 = 2*precision.*recall./max(precision+recall,eps);
values = [mean(actual==predicted), mean(f1), recall'];
end

function fold = showFolds(process, numberOfFolds)
% Keep in sync with analyze_feature_value.m for the same ordered input rows.
process = double(process);
shows = unique(process,'stable');
assert(numel(shows)>=numberOfFolds, 'Liiga vähe saateid.');
counts = arrayfun(@(show) sum(process==show),shows);
[~,order] = sortrows([-counts(:),rand(size(shows(:)))],[1 2]);
loads = zeros(numberOfFolds,1); showFold = zeros(size(shows));
for index = order(:)'
    choices = find(loads==min(loads));
    selected = choices(randi(numel(choices)));
    showFold(index)=selected; loads(selected)=loads(selected)+counts(index);
end
fold = zeros(size(process));
for index=1:numel(shows), fold(process==shows(index))=showFold(index); end
assert(all(fold>=1 & fold<=numberOfFolds));
end

function result = writeResults(folder, models, importance, ablation, errors)
result.Models = cell2table(models, VariableNames={'Model','K','DistanceWeight', ...
    'CVAccuracy','TrainingAccuracy','CVMacroF1','RecallAccepted','RecallModified','RecallRejected','Status'});
result.PermutationImportance = cell2table(importance, VariableNames={ ...
    'Model','Predictor','ImportanceMean','ImportanceStd','Rank','Status'});
result.Ablation = cell2table(ablation, VariableNames={'Model','RemovedPredictor', ...
    'FullCVAccuracy','WithoutCVAccuracy','AccuracyDrop', ...
    'FullCVMacroF1','WithoutCVMacroF1','MacroF1Drop','Status'});
result.Errors = cell2table(errors, VariableNames={'Model','Stage','Error'});
% Give empty result columns their intended types if every attempt failed.
if isempty(models)
    for name = ["K","CVAccuracy","TrainingAccuracy","CVMacroF1", ...
            "RecallAccepted","RecallModified","RecallRejected"]
        result.Models.(name) = zeros(0,1);
    end
end
if isempty(importance)
    result.PermutationImportance.Predictor = strings(0,1);
    for name = ["ImportanceMean","ImportanceStd","Rank"]
        result.PermutationImportance.(name) = zeros(0,1);
    end
end
if isempty(ablation)
    result.Ablation.RemovedPredictor = strings(0,1);
    for name = ["FullCVAccuracy","WithoutCVAccuracy","AccuracyDrop", ...
            "FullCVMacroF1","WithoutCVMacroF1","MacroF1Drop"]
        result.Ablation.(name) = zeros(0,1);
    end
end
writetable(result.Models,fullfile(folder,'model_validation_results_knn.csv'));
writetable(result.PermutationImportance,fullfile(folder,'permutation_importance_all_models_knn.csv'));
writetable(result.Ablation,fullfile(folder,'feature_ablation_all_models_knn.csv'));
writetable(result.Errors,fullfile(folder,'errors_knn.csv'));
end
