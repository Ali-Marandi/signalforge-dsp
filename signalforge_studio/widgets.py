*** Begin Patch
*** Update File: signalforge_studio/widgets.py
@@
         for item in self._series:
             path = QPainterPath()
             stride = max(1, len(item.x) // max(2, self._plot_rect.width() * 2))
             first = True
             for index in range(0, len(item.x), stride):
                 point = self._point_for(item.x[index], item.y[index], bounds)
                 if first:
                     path.moveTo(point)
                     first = False
                 else:
                     path.lineTo(point)
             if (len(item.x) - 1) % stride:
                 point = self._point_for(item.x[-1], item.y[-1], bounds)
                 path.lineTo(point)
-            painter.setPen(QPen(item.color, 1.65))
-            painter.drawPath(path)
+            painter.setPen(QPen(item.color, 1.65))
+            painter.drawPath(path)
*** End Patch
