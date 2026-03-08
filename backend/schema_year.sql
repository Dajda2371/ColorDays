CREATE TABLE IF NOT EXISTS classes (
    class TEXT PRIMARY KEY,
    teacher TEXT,
    counts1 TEXT,
    counts2 TEXT,
    counts3 TEXT,
    iscountedby1 TEXT,
    iscountedby2 TEXT,
    iscountedby3 TEXT,
    state1 TEXT,
    state2 TEXT,
    state3 TEXT
);
CREATE TABLE IF NOT EXISTS students (
    code TEXT PRIMARY KEY,
    class TEXT,
    note TEXT,
    counts_classes TEXT
);
CREATE TABLE IF NOT EXISTS counts_monday (
    class_name TEXT,
    type TEXT,
    points INTEGER,
    count INTEGER,
    PRIMARY KEY (class_name, type, points)
);
CREATE TABLE IF NOT EXISTS counts_tuesday (
    class_name TEXT,
    type TEXT,
    points INTEGER,
    count INTEGER,
    PRIMARY KEY (class_name, type, points)
);
CREATE TABLE IF NOT EXISTS counts_wednesday (
    class_name TEXT,
    type TEXT,
    points INTEGER,
    count INTEGER,
    PRIMARY KEY (class_name, type, points)
);
