function outputs = analyze_feature_value(csvFile)
% Compare predictor use and value across classifiers.
% Run from project root: outputs = analyze_feature_value("log/training_data_b.csv")

if nargin < 1
    [name, folder] = uigetfile("*.csv", "Vali täielik training_data_b.csv");
    if isequal(name, 0), error("Faili ei valitud."); end
    csvFile = fullfile(folder, name);
end
csvFile = string(csvFile);
data = readtable(csvFile, TextType="string", VariableNamingRule="preserve");

predictors = ["duration_s"; "words"; "show_speaker_count"; "candidate_type"; ...
    "internal_speaker_change_count"; "distinct_speaker_count"; ...
    "dominant_speaker_coverage"; "nearest_change_edge_ratio"];
newPredictors = predictors(5:8);
required = ["process"; predictors; "decision"];
missing = setdiff(required, string(data.Properties.VariableNames));
if ~isempty(missing)
    error("Puuduvad veerud: %s. Vali täielik CSV, mitte 9 veeruga MATLABi tabel.", ...
        strjoin(missing, ", "));
end
data.candidate_type = categorical(data.candidate_type);
data.decision = categorical(data.decision, ["ACCEPTED", "MODIFIED", "REJECTED"]);
if any(isundefined(data.candidate_type)) || any(isundefined(data.decision))
    error("candidate_type või decision sisaldab tundmatuid väärtusi.");
end
if any(ismissing(data(:, cellstr(predictors))), "all")
    error("Mõnes mudeli atribuudis on puuduv väärtus.");
end

models = ["Fine Tree"; "Medium Tree"; "Coarse Tree"; "Kernel Naive Bayes"; ...
    "Linear SVM"; "Quadratic SVM"; "Cubic SVM"; "Fine Gaussian SVM"; ...
    "Medium Gaussian SVM"; "Coarse Gaussian SVM"; "SVM Kernel"; ...
    "Logistic Regression Kernel"; "Boosted Trees"; "Bagged Trees"; "RUSBoosted Trees"];

rng(20261017, "twister");
fold = showFolds(data.process, 5);
numPermutations = 30;
modelRows = table(Size=[0 5], VariableTypes=["string","double","double","string","string"], ...
    VariableNames=["Model","CVAccuracy","TrainingAccuracy","Status","Error"]);
importanceRows = table(Size=[0 6], VariableTypes=["string","string","double","double","double","string"], ...
    VariableNames=["Model","Predictor","ImportanceMean","ImportanceStd","Rank","Status"]);
ablationRows = table(Size=[0 6], VariableTypes=["string","string","double","double","double","string"], ...
    VariableNames=["Model","RemovedPredictor","FullCVAccuracy","WithoutCVAccuracy","AccuracyDrop","Status"]);

for modelIndex = 1:numel(models)
    modelName = models(modelIndex);
    fprintf("[%d/%d] %s\n", modelIndex, numel(models), modelName);
    try
        fullCV = cvAccuracy(modelName, data, predictors, fold, modelIndex);
        trainTable = data(:, cellstr([predictors; "decision"]));
        rng(100000 + modelIndex, "twister");
        mdl = trainClassifier(modelName, trainTable);
        fitted = predict(mdl, trainTable(:, cellstr(predictors)));
        trainingAccuracy = mean(fitted == trainTable.decision);
        modelRows(end+1,:) = {modelName, fullCV, trainingAccuracy, "OK", ""};

        rng(200000 + modelIndex, "twister");
        imp = permutationImportance(mdl, trainTable, "decision", ...
            NumPermutations=numPermutations, LossFun="classiferror");
        imp = sortrows(imp, "ImportanceMean", "descend");
        for row = 1:height(imp)
            importanceRows(end+1,:) = {modelName, string(imp.Predictor(row)), ...
                imp.ImportanceMean(row), imp.ImportanceStandardDeviation(row), row, "OK"};
        end

        % Retrain once without each predictor. Positive AccuracyDrop means
        % that removing the predictor made validation accuracy worse.
        for predictorIndex = 1:numel(predictors)
            reduced = predictors;
            reduced(predictorIndex) = [];
            withoutCV = cvAccuracy(modelName, data, reduced, fold, modelIndex);
            ablationRows(end+1,:) = {modelName, predictors(predictorIndex), ...
                fullCV, withoutCV, fullCV-withoutCV, "OK"};
        end
    catch exception
        warning("%s ebaõnnestus: %s", modelName, exception.message);
        modelRows(end+1,:) = {modelName, NaN, NaN, "FAILED", string(exception.message)};
        for predictorIndex = 1:numel(predictors)
            importanceRows(end+1,:) = {modelName,predictors(predictorIndex),NaN,NaN,NaN,"FAILED"};
            ablationRows(end+1,:) = {modelName,predictors(predictorIndex),NaN,NaN,NaN,"FAILED"};
        end
    end
end

summaryRows = table(Size=[numel(predictors) 9], ...
    VariableTypes=["string","logical","double","double","double","double","double","double","double"], ...
    VariableNames=["Predictor","IsNew","MeanPermutationImportance", ...
    "MedianPermutationImportance","MedianImportanceRank","ModelsUsingPredictor", ...
    "MeanAccuracyDrop","MedianAccuracyDrop","ModelsHelpedByPredictor"]);
for predictorIndex = 1:numel(predictors)
    predictor = predictors(predictorIndex);
    ir = importanceRows(importanceRows.Predictor==predictor & importanceRows.Status=="OK",:);
    ar = ablationRows(ablationRows.RemovedPredictor==predictor & ablationRows.Status=="OK",:);
    summaryRows(predictorIndex,:) = {predictor,ismember(predictor,newPredictors), ...
        mean(ir.ImportanceMean,"omitnan"),median(ir.ImportanceMean,"omitnan"), ...
        median(ir.Rank,"omitnan"),sum(ir.ImportanceMean>0), ...
        mean(ar.AccuracyDrop,"omitnan"),median(ar.AccuracyDrop,"omitnan"),sum(ar.AccuracyDrop>0)};
end
summaryRows = sortrows(summaryRows,"MeanAccuracyDrop","descend");

outputFolder = fileparts(csvFile);
if strlength(outputFolder)==0, outputFolder=pwd; end
writetable(modelRows,fullfile(outputFolder,"model_validation_results.csv"));
writetable(importanceRows,fullfile(outputFolder,"permutation_importance_all_models.csv"));
writetable(ablationRows,fullfile(outputFolder,"feature_ablation_all_models.csv"));
writetable(summaryRows,fullfile(outputFolder,"feature_value_summary.csv"));
save(fullfile(outputFolder,"feature_value_results.mat"), ...
    "modelRows","importanceRows","ablationRows","summaryRows","fold","predictors");
outputs = struct(Models=modelRows,PermutationImportance=importanceRows, ...
    Ablation=ablationRows,FeatureSummary=summaryRows);
disp("Positiivne AccuracyDrop tähendab, et tunnuse eemaldamine halvendas valideerimist.");
disp(summaryRows);
disp("Uute tunnuste detail:");
disp(summaryRows(ismember(summaryRows.Predictor,newPredictors),:));
end

function fold = showFolds(process, numberOfFolds)
process = double(process);
shows = unique(process,"stable");
counts = arrayfun(@(show) sum(process==show),shows);
[~,order] = sortrows([-counts(:),rand(size(shows(:)))],[1 2]);
loads = zeros(numberOfFolds,1);
showFold = zeros(size(shows));
for index = order(:)'
    choices = find(loads==min(loads));
    selected = choices(randi(numel(choices)));
    showFold(index)=selected;
    loads(selected)=loads(selected)+counts(index);
end
fold = zeros(size(process));
for index=1:numel(shows), fold(process==shows(index))=showFold(index); end
assert(all(fold>=1 & fold<=numberOfFolds));
for index=1:numel(shows), assert(numel(unique(fold(process==shows(index))))==1); end
end

function accuracy = cvAccuracy(modelName,data,predictors,fold,modelIndex)
correct=0; total=0;
for foldNumber=1:max(fold)
    trainRows=fold~=foldNumber; validationRows=fold==foldNumber;
    trainTable=data(trainRows,cellstr([predictors;"decision"]));
    rng(300000+1000*modelIndex+foldNumber,"twister");
    mdl=trainClassifier(modelName,trainTable);
    predicted=predict(mdl,data(validationRows,cellstr(predictors)));
    correct=correct+sum(predicted==data.decision(validationRows));
    total=total+sum(validationRows);
end
accuracy=correct/total;
end

function mdl = trainClassifier(modelName,tbl)
p=width(tbl)-1;
switch modelName
    case "Fine Tree", mdl=fitctree(tbl,"decision",MaxNumSplits=100);
    case "Medium Tree", mdl=fitctree(tbl,"decision",MaxNumSplits=20);
    case "Coarse Tree", mdl=fitctree(tbl,"decision",MaxNumSplits=4);
    case "Kernel Naive Bayes"
        d=repmat("kernel",1,p); names=string(tbl.Properties.VariableNames(1:end-1));
        d(names=="candidate_type")="mvmn";
        mdl=fitcnb(tbl,"decision",DistributionNames=cellstr(d));
    case "Linear SVM"
        mdl=fitcecoc(tbl,"decision",Learners=templateSVM(KernelFunction="linear",Standardize=true),Coding="onevsone");
    case "Quadratic SVM"
        mdl=fitcecoc(tbl,"decision",Learners=templateSVM(KernelFunction="polynomial",PolynomialOrder=2,Standardize=true),Coding="onevsone");
    case "Cubic SVM"
        mdl=fitcecoc(tbl,"decision",Learners=templateSVM(KernelFunction="polynomial",PolynomialOrder=3,Standardize=true),Coding="onevsone");
    case "Fine Gaussian SVM"
        mdl=fitcecoc(tbl,"decision",Learners=templateSVM(KernelFunction="gaussian",KernelScale=sqrt(p)/4,Standardize=true),Coding="onevsone");
    case "Medium Gaussian SVM"
        mdl=fitcecoc(tbl,"decision",Learners=templateSVM(KernelFunction="gaussian",KernelScale=sqrt(p),Standardize=true),Coding="onevsone");
    case "Coarse Gaussian SVM"
        mdl=fitcecoc(tbl,"decision",Learners=templateSVM(KernelFunction="gaussian",KernelScale=4*sqrt(p),Standardize=true),Coding="onevsone");
    case "SVM Kernel"
        mdl=fitcecoc(tbl,"decision",Learners=templateKernel(Learner="svm",Standardize=true),Coding="onevsone");
    case "Logistic Regression Kernel"
        mdl=fitcecoc(tbl,"decision",Learners=templateKernel(Learner="logistic",Standardize=true),Coding="onevsone");
    case "Boosted Trees"
        mdl=fitcensemble(tbl,"decision",Method="AdaBoostM2",Learners=templateTree(MaxNumSplits=20),NumLearningCycles=30,LearnRate=.1);
    case "Bagged Trees"
        mdl=fitcensemble(tbl,"decision",Method="Bag",Learners=templateTree(NumVariablesToSample="all"),NumLearningCycles=30);
    case "RUSBoosted Trees"
        mdl=fitcensemble(tbl,"decision",Method="RUSBoost",Learners=templateTree(MaxNumSplits=20),NumLearningCycles=30,LearnRate=.1);
    otherwise, error("Tundmatu mudel: %s",modelName);
end
end
