# power-meter

วัดว่าคอมใช้ไฟไปเท่าไหร่ แล้วคิดเป็นเงินบาทตามค่าไฟจริงของไทย รองรับทั้งมิเตอร์ปกติและมิเตอร์ TOU (กลางวันแพง กลางคืนถูก)

*Track how much electricity your PC uses and what it costs in Thai baht, including time-of-use (TOU) pricing.*

```
21:30:05 Peak     ประมาณ   98.4 W  0.63 ฿/ชม. | รอบนี้  1.204 ฿ | วันนี้ 0.512 kWh   2.87 ฿ | รวม   41.20 ฿
```

## ติดตั้ง

ต้องใช้ Windows และ Python 3.11 ขึ้นไป

```
git clone https://github.com/Tachsakorn/power-meter
cd power-meter
pip install .
copy config.example.toml config.toml
```

ถ้าอยากให้อ่านไฟ CPU ได้จริง ให้เปิด [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) แบบ Run as administrator แล้วไปที่ **Options → Remote Web Server → Run** ถ้าไม่เปิด โปรแกรมจะใช้ค่าประมาณแทน

## ใช้งาน

ดับเบิลคลิก `run.bat` เพื่อเปิดแอป ครั้งแรกจะติดตั้งสิ่งที่ต้องใช้ให้เอง

![Power Meter](docs/screenshot.png)

หน้าแอปเปลี่ยนสีตามช่วงค่าไฟ: สีแดดตอนช่วงแพง สีกลางคืนตอนช่วงถูก วงกลมคือนาฬิกา 24 ชั่วโมงที่บอกว่าช่วงไหนแพงหรือถูก และเข็มชี้เวลาตอนนี้

ใช้ผ่าน command line ก็ได้:

```
power-meter              # เปิดแอป
power-meter run          # วัดในหน้าต่าง console กด Ctrl+C เพื่อหยุด
power-meter report       # ดูสรุป 7 วันล่าสุด
power-meter report -d 30
```

ข้อมูลเก็บไว้ที่ `%LOCALAPPDATA%\power-meter\usage.json` ปิดแล้วเปิดใหม่ก็นับต่อจากเดิม

## เกม Build Your Reactor (ไม่บังคับ)

กดแท็บ **Build Your Reactor** บนหัวแอปเพื่อเล่นเกมสร้างโรงไฟฟ้าแบบ idle สร้างไดนาโม แผงโซลาร์ กังหันลม ห้องแล็บ แบตเตอรี่ ไปจนถึงเตาฟิชชันและฟิวชัน

- เกมแยกขาดจากมิเตอร์ ใช้เครดิตสมมติ (cr) ไม่ใช่เงินจริง และไม่ได้คิดจากไฟที่คอมใช้
- ค่าไฟจริง (฿/ชม.) ยังโชว์อยู่บนหัวหน้าเกม การวัดไฟทำงานต่อตลอดแม้เปิดเกมอยู่
- ภาพเคลื่อนไหวจะหยุดเมื่อไม่ได้เปิดแท็บเกม เกมจะได้ไม่กินไฟเอง
- เซฟอยู่ที่ `%LOCALAPPDATA%\power-meter\reactor-save.json` แยกจากข้อมูลค่าไฟ

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
node --test tests/js/*.test.js
ruff check . && ruff format .
```

## ข้อจำกัด

- ตอนนี้รองรับเฉพาะ Windows และวัด GPU ได้เฉพาะ NVIDIA
- ไดรเวอร์ของ LibreHardwareMonitor อาจโดน Windows Defender เตือน

## License

MIT. ฟอนต์ IBM Plex Sans Thai และ Mali ใช้ SIL Open Font License (ดู `OFL.txt` ในโฟลเดอร์ `fonts`)
