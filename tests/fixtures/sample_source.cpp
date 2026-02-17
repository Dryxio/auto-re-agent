#include "StdInc.h"
#include "CTrain.h"

void CTrain::ProcessControl() {
    if (m_nStatus == STATUS_TRAIN_MOVING) {
        float speed = m_fSpeed * CTimer::GetTimeStep();
        m_fDistanceTravelled += speed;
        if (m_fDistanceTravelled > m_fTotalPathLength) {
            m_fDistanceTravelled -= m_fTotalPathLength;
        }
        UpdateTrainNodes();
        ProcessPassengers();
    }
}

void CTrain::Shutdown() {
    // NOTSA_UNREACHABLE
    plugin::CallMethod<0x6F5900, CTrain*>(this);
}

void CTrain::UpdateSpeed() {
    return I_UpdateSpeed<false>();
}
