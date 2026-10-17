# power-meter

วัดว่าคอมใช้ไฟไปเท่าไหร่ แล้วคิดเป็นเงินบาทตามค่าไฟจริงของไทย รองรับทั้งมิเตอร์ปกติและมิเตอร์ TOU (กลางวันแพง กลางคืนถูก)

*Track how much electricity your PC uses and what it costs in Thai baht, including time-of-use (TOU) pricing.*

```
21:30:05 Peak     ประมาณ   98.4 W  0.63 ฿/ชม. | รอบนี้  1.204 ฿ | วันนี้ 0.512 kWh   2.87 ฿ | รวม   41.20 ฿
```

## ติดตั้ง

ต้องใช้ Windows และ Python 3.11 ขึ้นไป

```
git clone https://github.com/<your-name>/power-meter
cd power-meter
pip install .
copy config.example.toml config.toml
```

ถ้าอยากให้อ่านไฟ CPU ได้จริง ให้เปิด [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) แบบ Run as administrator แล้วไปที่ **Options → Remote Web Server → Run** ถ้าไม่เปิด โปรแกรมจะใช้ค่าประมาณแทน

## ใช้งาน

```
power-meter            # เริ่มวัด กด Ctrl+C เพื่อหยุด
power-meter report     # ดูสรุป 7 วันล่าสุด
power-meter report -d 30
```

ข้อมูลเก็บไว้ที่ `%LOCALAPPDATA%\power-meter\usage.json` ปิดแล้วเปิดใหม่ก็นับต่อจากเดิม

## วัดยังไง

| แหล่ง | วิธีอ่านค่า | ความแม่น |
|---|---|---|
| แบตเตอรี่ | ชิปในแบตวัดแรงดันและกระแส อ่านผ่าน WMI | แม่นที่สุด (ตอนถอดปลั๊ก วัดได้ทั้งเครื่อง) |
| GPU (NVIDIA) | เซนเซอร์บนการ์ดจอ อ่านผ่าน NVML | ดี |
| CPU | ค่า package power จาก LibreHardwareMonitor | ดี |
| จอ, RAM, SSD, พัดลม | ไม่มีเซนเซอร์ ใช้ค่า `base_watts` | ค่าประมาณ |

ตอนถอดปลั๊ก โปรแกรมใช้ค่าจากแบตโดยตรง ตอนเสียบปลั๊ก จะเอาค่าทุกส่วนมารวมกัน บวกไฟที่กำลังชาร์จเข้าแบต แล้วหารด้วยประสิทธิภาพของอแดปเตอร์

ถ้าอยากได้ค่าที่แม่นขึ้น ให้เสียบปลั๊กวัดไฟ (wattmeter) ที่ผนัง เทียบค่ากับโปรแกรม แล้วปรับ `base_watts` ใน `config.toml`

## ค่าไฟ

ค่าเริ่มต้นเป็นอัตราบ้านอยู่อาศัยของ กฟน./กฟภ. งวด ก.ย.–ธ.ค. 2569

- TOU Peak (จ–ศ 09:00–22:00): 5.7982 ฿ + Ft
- TOU Off-peak (นอกเวลาด้านบน, ส–อา, วันหยุดราชการ): 2.6369 ฿ + Ft
- Ft = 0.1623 ฿/หน่วย, VAT 7%

ค่า Ft เปลี่ยนทุก 4 เดือน ให้แก้ใน `config.toml` ค่าไฟของวันที่บันทึกไปแล้วจะยังคิดตามราคาเดิม

## พัฒนา

```
pip install -e ".[dev]"
pytest
ruff check . && ruff format .
```

## ข้อจำกัด

- ตอนนี้รองรับเฉพาะ Windows และวัด GPU ได้เฉพาะ NVIDIA
- ไดรเวอร์ของ LibreHardwareMonitor อาจโดน Windows Defender เตือน

## License

MIT
