# Jatayu USB Studio 1.1.0 RC1 · package revision 3

Clone USB excludes the selected source drive from the destination picker. With just the source connected, the destination picker asks for a second drive. The Clone button requires two distinct selections and enough destination capacity. Existing backend checks still apply.

USB Repair labels partitions explicitly and shows the parent drive, partition path, capacity and filesystem. A drive without partitions can be presented as a whole-drive filesystem.

The offscreen Qt regression test uses synthetic one-drive and two-drive inventories. This update was tested without writing to a physical USB drive.
