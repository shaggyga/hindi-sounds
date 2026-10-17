from pathlib import Path
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QColor,QFont,QFontDatabase,QImage,QPainter
from PySide6.QtWidgets import QApplication
app=QApplication([])
root=Path(__file__).resolve().parents[1]
QFontDatabase.addApplicationFont(str(root/'assets/fonts/hindi.ttf'))
image=QImage(256,256,QImage.Format.Format_ARGB32);image.fill(Qt.GlobalColor.transparent)
painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(QColor('#171d28'));painter.drawRoundedRect(QRectF(0,0,256,256),40,40)
painter.setPen(QColor('#8ec5ff'));font=QFont('Noto Sans Devanagari');font.setPixelSize(174);painter.setFont(font)
painter.drawText(QRectF(12,8,232,240),Qt.AlignmentFlag.AlignCenter,'अ');painter.end()
assert image.save(str(root/'assets/hindi-sounds.ico'))
