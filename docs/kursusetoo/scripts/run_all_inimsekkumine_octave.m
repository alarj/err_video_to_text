function outputs = run_all_inimsekkumine_octave ()
  % Käivita kõik kuus binaarset 498 variandi katset järjest.
  jobs = {
    "log/training_data_b_inimsekkumine.csv", "log/test1_data_b_inimsekkumine.csv", "b1";
    "log/training_data_b_inimsekkumine.csv", "log/test2_data_b_inimsekkumine.csv", "b2";
    "log/training_data_c_inimsekkumine.csv", "log/test_data_c1_inimsekkumine.csv", "c1";
    "log/training_data_d_inimsekkumine.csv", "log/test_data_d1_inimsekkumine.csv", "d1";
    "log/training_data_x_inimsekkumine.csv", "log/test_data_x1_inimsekkumine.csv", "x1";
    "log/training_data_y_inimsekkumine.csv", "log/test_data_y1_inimsekkumine.csv", "y1";
  };
  outputs = cell (size (jobs, 1), 1);
  for i = 1:size (jobs, 1)
    fprintf ("=== %s ===\n", jobs{i, 3});
    outputs{i} = test_all_models_inimsekkumine_octave (jobs{i, 1}, jobs{i, 2}, jobs{i, 3});
  endfor
  save (fullfile (pwd (), "log", "inimsekkumine_koik_katsed.mat"), "outputs", "jobs");
endfunction
