import React, { useState } from "react";
import { Box, Button, Typography, Alert, MenuItem, Select, FormControl, InputLabel, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from "@mui/material";
import { LocalizationProvider, DatePicker } from "@mui/x-date-pickers";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { ja } from "date-fns/locale";  
import axios from "axios";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";

dayjs.extend(utc);
dayjs.extend(timezone);

interface RaceResult {
  rank: string;
  waku: string;
  horse_num: string;
  name: string;
  age: string;
  weight: string;
  jockey: string;
  time: string;
  sa: string;
  ninki: string;
  odds: string;
}

const RaceForm: React.FC = () => {
  const [racecourse, setRacecourse] = useState("");
  const [selectedDate, setDate] = useState<Date | null>(null);
  const [raceNum, setRaceNum] = useState<string>("");
  const [error, setError] = useState("");
  const [results, setResults] = useState<RaceResult[] | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");  
    setResults(null); 
    const formattedDate = selectedDate ? dayjs(selectedDate).tz("Asia/Tokyo").format("YYYY-MM-DD") : "";

    console.log({
      racecourse,
      selectedDate: formattedDate,
      race_num: raceNum
    });
    try {
      const response = await axios.post<RaceResult[]>("https://grade.annko.jp/api/keiba/race_result", {
        racecourse,
        selectedDate: formattedDate, 
        race_num: raceNum,
      });
      
      setResults(response.data);  
    } catch (err) {
      setError("結果が取得できませんでした。");  
    }
  };

  const racecourses = [
    "札幌", "函館", "福島", "新潟", 
    "東京", "中山", "中京", "京都", 
    "阪神", "小倉"
  ];

  return (
    <Box sx={{ maxWidth: 840, margin: "auto", padding: 3 }}>
      <Typography variant="h5" gutterBottom>
        レース情報検索
      </Typography>
      <form onSubmit={handleSubmit}>
        {/* 開催地 */}
        <FormControl fullWidth margin="normal">
          <InputLabel>開催地</InputLabel>
          <Select
            value={racecourse}
            onChange={(e) => setRacecourse(e.target.value)}
            label="開催地"
          >
            {racecourses.map((course, index) => (
              <MenuItem key={index} value={course}>
                {course}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* 日付（カレンダー） */}
        <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={ja}>
          <DatePicker
            label="YYYY-MM-DD"
            value={selectedDate}
            onChange={(newDate) => setDate(newDate)}
          />
        </LocalizationProvider>

        {/* レース数 */}
        <FormControl fullWidth margin="normal">
          <InputLabel>レース数</InputLabel>
          <Select
            value={raceNum}
            onChange={(e) => setRaceNum(e.target.value.toString())}
            label="レース数"
          >
            {[...Array(12).keys()].map((i) => (
              <MenuItem key={i + 1} value={i + 1}>
                {i + 1}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <Button
          type="submit"
          variant="contained"
          color="primary"
          fullWidth
          sx={{ mt: 2 }}
        >
          検索
        </Button>
      </form>

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}
      {results && (
        <Paper sx={{ mt: 4 }}>
          <Typography variant="h6" align="center" sx={{ p: 2 }}>レース結果</Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  {["順位", "枠", "馬番", "馬名", "年齢", "体重", "騎手", "タイム", "着差", "人気", "単勝オッズ"].map((header) => (
                    <TableCell key={header} align="center">{header}</TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {results.map((result, index) => (
                  <TableRow key={index}>
                    <TableCell align="center">{result.rank}</TableCell>
                    <TableCell align="center">{result.waku}</TableCell>
                    <TableCell align="center">{result.horse_num}</TableCell>
                    <TableCell align="center">{result.name}</TableCell>
                    <TableCell align="center">{result.age}</TableCell>
                    <TableCell align="center">{result.weight}</TableCell>
                    <TableCell align="center">{result.jockey}</TableCell>
                    <TableCell align="center">{result.time}</TableCell>
                    <TableCell align="center">{result.sa}</TableCell>
                    <TableCell align="center">{result.ninki}</TableCell>
                    <TableCell align="center">{result.odds}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}
    </Box>
  );
};

export default RaceForm;
