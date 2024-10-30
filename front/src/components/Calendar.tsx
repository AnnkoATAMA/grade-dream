import { Box } from '@mui/material';
import { DatePicker, LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import dayjs from 'dayjs';
import 'dayjs/locale/ja';

dayjs.locale('ja'); // カレンダーの曜日のフォーマット

interface CalendarProps {
  selectedDate: dayjs.Dayjs | null; // 選択された日付の型
  setSelectedDate: (date: dayjs.Dayjs | null) => void; // 日付を更新するための関数
}

export const Calendar: React.FC<CalendarProps> = ({ selectedDate, setSelectedDate }): JSX.Element => {
  return (
    <Box sx={{ p: 10, display: 'flex', justifyContent: 'center' }}>
      <LocalizationProvider dateAdapter={AdapterDayjs}>
        <DatePicker
          label="日本語"
          value={selectedDate} // 選択された日付を設定
          onChange={(newValue) => setSelectedDate(newValue)} // 日付変更時の処理
          format="YYYY/MM/DD" // テキストエリア内のフォーマット
          slotProps={{ calendarHeader: { format: 'YYYY年MM月' } }} // カレンダーヘッダーのフォーマット
        />
      </LocalizationProvider>
    </Box>
  );
};

export default Calendar;
