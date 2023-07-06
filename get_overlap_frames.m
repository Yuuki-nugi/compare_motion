% csvファイルからデータを取り込む

[file, path] = uigetfile('*.csv', 'CSVファイルを選択してください');
data = readmatrix(fullfile(path, file));

[file, path] = uigetfile('*.mp4', '動画ファイルを選択してください');
video_reader = VideoReader(fullfile(path, file));
fps = video_reader.FrameRate;

%%

right_peaks_indexes = get_peaks(data(:, 86));
right_angles = get_angles([right_peaks_indexes, data(right_peaks_indexes, :)], true);

left_peaks_indexes = get_peaks(data(:, 83));
left_angles = get_angles([left_peaks_indexes, data(left_peaks_indexes, :)], false);

timings = get_timings(data(4:end, 86), data(4:end, 83), fps);

% csvフォーマット
% ----- angles
% 右脚 = 0, 左脚 = 1
% 脚上げ時のframe
% 股関節角度
% 足首と腿の角度
% 腿の角度(地面からの垂線との角度)
% 足首の角度(地面からの垂線との角度)
% 逆足が上がり切るまでのフレーム数
% ----- timings
% 接地frame
% 前側の足が上がり切ったframe
% (前側の足が上がり切ったframe - 接地frame) / fps

angles_for_csv = [];
for i = 1: size(right_peaks_indexes, 1)
    angles_for_csv(:, i) = [
        0;
        right_peaks_indexes(i);
        right_angles(i, :).'
        ];
end
for i = 1: size(left_peaks_indexes, 1)
    angles_for_csv(:, size(right_peaks_indexes, 1) + i) = [
        1;
        left_peaks_indexes(i);
        left_angles(i, :).'
        ];
end

split_path = split(path,"/");
test_name = string(split_path(end-1));

writematrix(angles_for_csv, 'data/' + test_name + '/angles.csv');
writematrix(timings, 'data/' + test_name + '/timings.csv');

%%
function result = get_peaks(data)

    [pks,upper_vertices_indexes] = findpeaks(data,'MinPeakProminence',20,'MinPeakDistance',12);
    
    index_list = zeros(1, size(data, 1));
    for i = 1: size(data, 1)
        index_list(1, i) = i;
    end

    vertices = [upper_vertices_indexes, pks];

    f = figure;
    plot(index_list,data,vertices(:, 1),vertices(:, 2),"o")
    selected_peaks  = ginput();

    result = get_close(vertices, selected_peaks(:, 1));

    close(f);
end

function result = get_close(vertices, selected)
    result = zeros(size(selected, 1), 1);
    for i = 1:size(selected(), 1)
       diff = abs(vertices(:, 1) - selected(i, 1)');
       [~, index] = min(diff);
       result(i, 1) = vertices(index, 1);
    end
end

function result = get_angles(data, is_right)
    if is_right
        raised_ankle = data(:, 86:87);
        raised_knee = data(:, 80:81);
        raised_hip = data(:, 74:75);
        supporting_ankle = data(:, 83:84);
        supporting_knee = data(:, 77:78);
        supporting_hip = data(:, 71:72) %% ; つけると変なエラーが出る
    else 
        raised_ankle = data(:, 83:84);
        raised_knee = data(:, 77:78);
        raised_hip = data(:, 71:72);
        supporting_ankle = data(:, 86:87);
        supporting_knee = data(:, 80:81);
        supporting_hip = data(:, 74:75);
    end

    result = zeros(size(data, 1), 5);
    for i = 1: size(data, 1)
        result(i, 1) = calculate_angle( ...
            raised_knee(i, :) - raised_hip(i, :), ...
            supporting_knee(i, :) - supporting_hip(i, :), ...
            false);
        result(i, 2) = calculate_angle( ...
            raised_ankle(i, :) - (raised_hip(i, :) + supporting_hip(i, :))/2, ...
            supporting_ankle(i, :) - (raised_hip(i, :) + supporting_hip(i, :))/2, ...
            false);
        result(i, 3) = calculate_angle( ...
            raised_knee(i, :) - raised_hip(i, :), ...
            [raised_hip(i, 1), 0] - raised_hip(i, :), ...
            false);
        result(i, 4) = calculate_angle( ...
            raised_ankle(i, :) - raised_hip(i, :), ...
            supporting_knee(i, :) - supporting_hip(i, :), ...
            false);
        result(i, 5) = calculate_angle( ...
            raised_ankle(i, :) - raised_hip(i, :), ...
            [raised_hip(i, 1), 0] - raised_hip(i, :), ...
            false);
    end
end

function angle_rad = calculate_angle(a, b, is_negative)
    % a,bの2つのベクトルを渡す。
    dot_product = dot(a, b, 2); % 2次元目で内積を計算
    
    % ベクトルの大きさを求める
    a_norm = vecnorm(a, 2, 2); % 2次元目でベクトルの大きさを計算
    b_norm = vecnorm(b, 2, 2); % 2次元目でベクトルの大きさを計算
    
    % 角度を求める（ラジアンから度に変換）
    angle_rad = acosd(dot_product ./ (a_norm .* b_norm));

    if is_negative
        angle_rad = 180 - angle_rad;
    end
end

function result = get_timings(right, left, fps)
    index_list = zeros(1, size(right, 1));
    for i = 1: size(right, 1)
        index_list(1, i) = i;
    end

    f = figure;
    hold on

    for i = 1: 2
        if i == 1
            data = right;
        else 
            data = left;
        end
        [pks,upper_vertices_indexes] = findpeaks(data,'MinPeakProminence',20,'MinPeakDistance',12);
        lower_vertices_indexes = islocalmin(data, 'MinProminence',20,'MinSeparation',12);
        
        lower_vertices = [index_list(lower_vertices_indexes).', data(lower_vertices_indexes)];
        upper_vertices = [upper_vertices_indexes, pks];
        vertices = [lower_vertices; upper_vertices];
        
        plot(index_list,data,vertices(:, 1),vertices(:, 2),"o")

        if i == 1
            right_vertices = vertices;
        else
            left_vertices = vertices;
        end
    end
    
    selected_peaks  = ginput();
    selected_peaks = get_close([right_vertices; left_vertices], selected_peaks(:, 1));

    for i = 1:size(selected_peaks, 1)/2
        result(:, i) = [
            selected_peaks(i*2-1, 1);
            selected_peaks(i*2, 1);
            (selected_peaks(i*2, 1)-selected_peaks(i*2-1, 1)) / fps
            ]
    end

    hold off
    close(f);
end
