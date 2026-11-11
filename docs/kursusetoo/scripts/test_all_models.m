function outputs = test_all_models(trainingFile, testFile)
% Refit the frozen configurations on TRAIN ONLY, then evaluate external Test1.
% outputs = test_all_models("training_data_b.csv", "test1_data_b.csv")
% Previous analysis scripts did not save fitted model objects.
if nargin < 1, trainingFile = "training_data_b.csv"; end
if nargin < 2, testFile = "test1_data_b.csv"; end
train = readtable(trainingFile, TextType="string", VariableNamingRule="preserve");
test = readtable(testFile, TextType="string", VariableNamingRule="preserve");
predictors = ["duration_s";"words";"show_speaker_count";"candidate_type"; ...
    "internal_speaker_change_count";"distinct_speaker_count"; ...
    "dominant_speaker_coverage";"nearest_change_edge_ratio"];
classes = ["ACCEPTED";"MODIFIED";"REJECTED"];
validateFrozenCohorts(train,test,predictors,classes);
assert(isempty(intersect(train.process,test.process)), 'Saated kattuvad!');
assert(isempty(intersect(train.candidate,test.candidate)), 'Kandidaadid kattuvad!');
for data = {train,test}
    t = data{1};
    assert(all(ismember(string(t.decision),classes)));
    assert(~any(ismissing(t.candidate_type)));
    for j = [1:3 5:8]
        assert(isnumeric(t.(predictors(j))) && all(isfinite(t.(predictors(j)))), ...
            'Puuduv või vigane tunnus: %s', predictors(j));
    end
end
actual = string(test.decision);
train.decision = categorical(train.decision,classes);
% Category dictionary comes only from training, never from test labels/rows.
levels = unique(string(train.candidate_type),'sorted');
assert(all(ismember(string(test.candidate_type),levels)), ...
    'Testis on uus candidate_type; üldmudelite jaoks puudub varasem reegel.');
train.candidate_type = categorical(train.candidate_type,levels);
test.candidate_type = categorical(test.candidate_type,levels);
[fullX,testX,groups,encoding] = encode(train,test,predictors);

models = ["Fine Tree";"Medium Tree";"Coarse Tree";"Kernel Naive Bayes"; ...
    "Linear SVM";"Quadratic SVM";"Cubic SVM";"Fine Gaussian SVM"; ...
    "Medium Gaussian SVM";"Coarse Gaussian SVM";"SVM Kernel"; ...
    "Logistic Regression Kernel";"Boosted Trees";"Bagged Trees";"RUSBoosted Trees"];
removedSets = [{[]},arrayfun(@(j) j,1:8,UniformOutput=false),{[5 6]},{5:8}];
variants = ["full";predictors;"both_speaker_counts";"all_four_new_features"];
% 15 * 9 ordinary + 33 * 11 kNN = 498 fixed configurations.
plan = cell(0,7);
for m = 1:numel(models)
    for v = 1:9
        plan(end+1,:) = {models(m),v,NaN,"",100000+m,m,"other"}; %#ok<AGROW>
    end
end
for k = [1 3 5 7 10 15 21 31 51 75 100]
    for weight = ["equal","inverse","squaredinverse"]
        for v = 1:11
            plan(end+1,:) = {"KNN k="+k+" "+weight,v,k,weight,20261017,0,"knn"}; %#ok<AGROW>
        end
    end
end
previousRng = rng; cleanup = onCleanup(@() rng(previousRng)); %#ok<NASGU>
base = fileparts(string(testFile));
if strlength(base)==0, base=string(pwd); end
folder = string(tempname(char(base)))+"_test1";
mkdir(folder); mkdir(fullfile(folder,"models"));
fprintf('Tulemuste kaust: %s\n',folder);
matlabVersion = version; toolboxes = ver;
save(fullfile(folder,"settings_test1.mat"),"plan","predictors","variants", ...
    "removedSets","encoding","classes","trainingFile","testFile", ...
    "train","test","matlabVersion","toolboxes");
copyfile(mfilename('fullpath')+".m",fullfile(folder,"test_all_models.m"));
summary = cell(0,10); perClass = cell(0,14); confusion = cell(0,5);
predictions = cell(0,6); errors = cell(0,3);
for n = 1:size(plan,1)
    modelName = plan{n,1}; v = plan{n,2}; seed = plan{n,5};
    variant = variants(v); family = plan{n,7};
    keep = ~ismember(1:8,removedSets{v}); selected = predictors(keep);
    fprintf('[%d/%d] %s / %s\n',n,size(plan,1),modelName,variant);
    try
        rng(seed,'twister');
        if family=="knn"
            columns = ~ismember(groups,removedSets{v});
            mdl = trainKNN(fullX(:,columns),train.decision,plan{n,3},plan{n,4});
            predicted = string(predict(mdl,testX(:,columns)));
            fitted = string(predict(mdl,fullX(:,columns)));
        else
            mdl = trainClassifier(modelName,train(:,cellstr([selected;"decision"])));
            predicted = string(predict(mdl,test(:,cellstr(selected))));
            fitted = string(predict(mdl,train(:,cellstr(selected))));
        end
        assert(all(ismember(predicted,classes)) && numel(predicted)==height(test));
        [overall,metrics,C] = scorePredictions(actual,predicted,classes);
        save(fullfile(folder,"models",sprintf('model_%03d.mat',n)), ...
            "mdl","modelName","variant","selected","encoding","family","seed");
        summary(end+1,:) = {modelName,variant,family,mean(fitted==string(train.decision)), ...
            overall(1),overall(2),overall(3),overall(4),height(test),"OK"}; %#ok<AGROW>
        for c = 1:3
            perClass(end+1,:) = [{modelName,variant,classes(c)},num2cell(metrics(c,:))]; %#ok<AGROW>
            for d = 1:3
                confusion(end+1,:) = {modelName,variant,classes(c),classes(d),C(c,d)}; %#ok<AGROW>
            end
        end
        for i = 1:height(test)
            predictions(end+1,:) = {modelName,variant,test.process(i),test.candidate(i),actual(i),predicted(i)}; %#ok<AGROW>
        end
    catch exception
        errors(end+1,:) = {modelName,variant,string(getReport(exception,'extended','hyperlinks','off'))}; %#ok<AGROW>
        summary(end+1,:) = {modelName,variant,family,NaN,NaN,NaN,NaN,NaN,height(test),"FAILED"}; %#ok<AGROW>
        warning('%s / %s: %s',modelName,variant,exception.message);
    end
    % Checkpoints retain completed work without overwriting older experiment folders.
    outputs = writeOutputs(folder,summary,perClass,confusion,predictions,errors);
end
outputs.OutputFolder = folder;
save(fullfile(folder,"results_test1.mat"),"outputs");
disp(outputs.Models);
fprintf('Valmis. Õnnestus %d/%d; vigu %d.\n',sum(string(outputs.Models.Status)=="OK"),size(plan,1),height(outputs.Errors));
end

function [overall,metrics,C] = scorePredictions(actual,predicted,classes)
C = zeros(3);
for a = 1:3
    for b = 1:3
        C(a,b)=sum(actual==classes(a) & predicted==classes(b));
    end
end
tp=diag(C); support=sum(C,2); fn=support-tp;
fp=sum(C,1)'-tp; tn=sum(C,'all')-tp-fn-fp;
precision=ratio(tp,tp+fp); recall=ratio(tp,tp+fn);
fpr=ratio(fp,fp+tn); fnr=ratio(fn,fn+tp); specificity=ratio(tn,tn+fp);
f1=ratio(2*tp,2*tp+fp+fn);
metrics=[support,tp,fp,tn,fn,precision,recall,f1,fpr,fnr,specificity];
overall=[sum(tp)/sum(C,'all'),mean(f1),mean(recall),sum(f1.*support)/sum(support)];
end

function z = ratio(a,b)
z=a./b; z(b==0)=NaN; % Undefined rates are not silently reported as zero.
end

function outputs = writeOutputs(folder,summary,perClass,confusion,predictions,errors)
outputs.Models=cell2table(summary,VariableNames={'Model','Variant','Family', ...
    'TrainingAccuracy','Accuracy','MacroF1','BalancedAccuracy','WeightedF1','TestRows','Status'});
outputs.PerClass=cell2table(perClass,VariableNames={'Model','Variant','Class', ...
    'Support','TP','FP','TN','FN','Precision','Recall_TPR','F1','FPR','FNR','Specificity_TNR'});
outputs.Confusion=cell2table(confusion,VariableNames={'Model','Variant','Actual','Predicted','Count'});
outputs.Predictions=cell2table(predictions,VariableNames={'Model','Variant','Process','Candidate','Actual','Predicted'});
outputs.Errors=cell2table(errors,VariableNames={'Model','Variant','Error'});
for name = ["Models","PerClass","Confusion","Predictions","Errors"]
    writetable(outputs.(name),fullfile(folder,lower(name)+"_test1.csv"));
end
end

function validateFrozenCohorts(train,test,predictors,classes)
% Java-vaba sisendikontroll. SHA-256 jääb manifestidesse väliseks kontrolliks.
required = ["process";"candidate";predictors;"decision"];
assert(isempty(setdiff(required,string(train.Properties.VariableNames))), ...
    'Treeningfailist puuduvad nõutud veerud.');
assert(isempty(setdiff(required,string(test.Properties.VariableNames))), ...
    'Testfailist puuduvad nõutud veerud.');
assert(height(train)==1006, 'Treeningfailis peab olema 1006 rida.');
assert(height(test)==488, 'Test1 failis peab olema 488 rida.');
assert(isequal(sort(unique(train.process))', ...
    [31 32 34:42 44 47:50 53:55 57:59 61:67 69 71:72 75:78 81:82 84:86 88 90 93 95:101]), ...
    'Treeningfaili protsesside koosseis ei vasta fikseeritud valimile.');
expected = [14 130 170;15 179 221;16 222 249;18 296 334;19 335 373; ...
    20 374 395;21 396 406;22 407 444;23 445 462;24 463 504;25 505 528; ...
    26 567 611;27 612 649;28 650 671;29 672 709];
expectedPairs = zeros(488,2); cursor=0;
for i=1:height(expected)
    ids=(expected(i,2):expected(i,3))'; n=numel(ids);
    expectedPairs(cursor+(1:n),:)=[repmat(expected(i,1),n,1),ids]; cursor=cursor+n;
end
actualPairs=sortrows([double(test.process),double(test.candidate)],[1 2]);
assert(isequal(actualPairs,expectedPairs), ...
    'Test1 protsessi- ja kandidaadi-ID-d ei vasta fikseeritud 488-realisele valimile.');
assert(isequal(sort(string(test.decision)),sort(repelem(classes,[290 107 91]))), ...
    'Test1 klasside jaotus peab olema 290/107/91 (ACCEPTED/MODIFIED/REJECTED).');
assert(isequal(sort(string(train.decision)),sort(repelem(classes,[251 454 301]))), ...
    'Treeningu klasside jaotus peab olema 251/454/301 (ACCEPTED/MODIFIED/REJECTED).');
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

function mdl = trainKNN(X, y, k, weight)
mdl = fitcknn(X, y, NumNeighbors=k, Distance='euclidean', ...
    DistanceWeight=char(weight), Standardize=false, NSMethod='exhaustive', ...
    BreakTies='smallest', IncludeTies=false);
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


