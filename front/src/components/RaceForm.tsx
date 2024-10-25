import React, { useState } from "react";
import axios from "axios";
import { Box, TextField, Button, Typography, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Alert } from '@mui/material';

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
  const [count, setCount] = useState("");
  const [race_date, setRaceDate] = useState("");
  const [raceNum, setRaceNum] = useState("");
  const [results, setResults] = useState<RaceResult[] | null>(null);
  const [error, setError] = useState("");

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    setResults(null);

    try {
      const response = await axios.post<RaceResult[]>("http://localhost:8000/race_result", {
        racecourse,
        count,
        race_date,
        race_num: raceNum,
      });
      setResults(response.data);
    } catch (err) {
      setError("結果が取得できませんでした。");
    }
  };

  return (
    <Box sx={{ maxWidth: 840, margin: 'auto', padding: 3 }}>
      <Typography variant="h5" gutterBottom>レース情報検索</Typography>
      <form onSubmit={handleSubmit}>
        <TextField
          fullWidth
          label="開催地"
          variant="outlined"
          value={racecourse}
          onChange={(e) => setRacecourse(e.target.value)}
          margin="normal"
        />
        <TextField
          fullWidth
          label="回数"
          variant="outlined"
          value={count}
          onChange={(e) => setCount(e.target.value)}
          margin="normal"
        />
        <TextField
          fullWidth
          label="日数"
          variant="outlined"
          value={race_date}
          onChange={(e) => setRaceDate(e.target.value)}
          margin="normal"
        />
        <TextField
          fullWidth
          label="レース数"
          variant="outlined"
          value={raceNum}
          onChange={(e) => setRaceNum(e.target.value)}
          margin="normal"
        />
        <Button type="submit" variant="contained" color="primary" fullWidth sx={{ mt: 2 }}>検索</Button>
      </form>

      {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}

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
