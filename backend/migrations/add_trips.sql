-- 行程表
CREATE TABLE IF NOT EXISTS trips (
    trip_id TEXT PRIMARY KEY,
    share_code TEXT UNIQUE NOT NULL,
    name TEXT DEFAULT '未命名行程',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 行程景点（协作选择）
CREATE TABLE IF NOT EXISTS trip_pois (
    trip_id TEXT NOT NULL,
    poi_id INTEGER NOT NULL,
    day_number INTEGER DEFAULT 1,
    order_index INTEGER DEFAULT 0,
    notes TEXT,
    added_by TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trip_id, poi_id),
    FOREIGN KEY (trip_id) REFERENCES trips(trip_id),
    FOREIGN KEY (poi_id) REFERENCES pois(id)
);

-- 参与者（可选，记录昵称）
CREATE TABLE IF NOT EXISTS trip_members (
    trip_id TEXT NOT NULL,
    nickname TEXT NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trip_id, nickname),
    FOREIGN KEY (trip_id) REFERENCES trips(trip_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_trips_share_code ON trips(share_code);
CREATE INDEX IF NOT EXISTS idx_trip_pois_trip_id ON trip_pois(trip_id);
CREATE INDEX IF NOT EXISTS idx_trip_members_trip_id ON trip_members(trip_id);
